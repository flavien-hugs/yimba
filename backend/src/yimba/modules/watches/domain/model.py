from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Iterable

from yimba.shared.errors import InvalidInput
from yimba.shared.ids import new_id
from yimba.shared.source import SourceKind
from yimba.shared.text import slugify

ALLOWED_FREQUENCIES_MINUTES = (15, 60, 360, 1440)
MAX_KEYWORDS = 20


@dataclass(frozen=True, slots=True)
class Frequency:
    minutes: int = 60

    def __post_init__(self) -> None:
        if self.minutes not in ALLOWED_FREQUENCIES_MINUTES:
            raise InvalidInput(f"frequency must be one of {ALLOWED_FREQUENCIES_MINUTES} minutes")


@dataclass(frozen=True, slots=True)
class AlertThreshold:
    """Raise an alert when the negative share reaches ``negative_share`` over at least ``min_mentions``."""

    negative_share: float = 0.4
    min_mentions: int = 20

    def __post_init__(self) -> None:
        if not 0.0 < self.negative_share <= 1.0:
            raise InvalidInput("negative_share must be in ]0, 1]")
        if self.min_mentions < 1:
            raise InvalidInput("min_mentions must be >= 1")


def _clean_unique(values: Iterable[str], *, lower: bool = False) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for value in values:
        cleaned = " ".join(value.split())
        if lower:
            cleaned = cleaned.lower()
        if cleaned:
            seen.setdefault(cleaned, None)
    return tuple(seen)


@dataclass(slots=True)
class Watch:
    id: str
    owner_id: str
    name: str
    slug: str
    keywords: tuple[str, ...]
    sources: tuple[SourceKind, ...]
    languages: tuple[str, ...]
    countries: tuple[str, ...]
    frequency: Frequency
    threshold: AlertThreshold
    active: bool
    created_at: datetime
    updated_at: datetime = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.updated_at is None:
            self.updated_at = self.created_at

    @classmethod
    def create(
        cls,
        *,
        owner_id: str,
        name: str,
        keywords: Iterable[str],
        sources: Iterable[SourceKind],
        languages: Iterable[str] = ("fr",),
        countries: Iterable[str] = ("CI",),
        frequency: Frequency | None = None,
        threshold: AlertThreshold | None = None,
        now: datetime,
    ) -> "Watch":
        cleaned_name = " ".join(name.split())
        if not cleaned_name:
            raise InvalidInput("name must not be empty")
        watch = cls(
            id=new_id(),
            owner_id=owner_id,
            name=cleaned_name,
            slug=slugify(cleaned_name),
            keywords=_clean_unique(keywords),
            sources=tuple(dict.fromkeys(sources)),
            languages=_clean_unique(languages, lower=True),
            countries=_clean_unique((c.upper() for c in countries)),
            frequency=frequency or Frequency(),
            threshold=threshold or AlertThreshold(),
            active=True,
            created_at=now,
        )
        watch._validate()
        return watch

    def revise(
        self,
        *,
        now: datetime,
        name: str | None = None,
        keywords: Iterable[str] | None = None,
        sources: Iterable[SourceKind] | None = None,
        languages: Iterable[str] | None = None,
        countries: Iterable[str] | None = None,
        frequency: Frequency | None = None,
        threshold: AlertThreshold | None = None,
        active: bool | None = None,
    ) -> None:
        candidate = replace(
            self,
            name=" ".join(name.split()) if name is not None else self.name,
            keywords=_clean_unique(keywords) if keywords is not None else self.keywords,
            sources=tuple(dict.fromkeys(sources)) if sources is not None else self.sources,
            languages=_clean_unique(languages, lower=True) if languages is not None else self.languages,
            countries=_clean_unique((c.upper() for c in countries)) if countries is not None else self.countries,
            frequency=frequency or self.frequency,
            threshold=threshold or self.threshold,
            active=self.active if active is None else active,
        )
        candidate._validate()
        for attribute in ("name", "keywords", "sources", "languages", "countries", "frequency", "threshold", "active"):
            setattr(self, attribute, getattr(candidate, attribute))
        if name is not None:
            self.slug = slugify(self.name)
        self.updated_at = now

    def _validate(self) -> None:
        if not self.name:
            raise InvalidInput("name must not be empty")
        if not self.keywords:
            raise InvalidInput("at least one keyword is required")
        if len(self.keywords) > MAX_KEYWORDS:
            raise InvalidInput(f"at most {MAX_KEYWORDS} keywords are allowed")
        if not self.sources:
            raise InvalidInput("at least one source is required")
