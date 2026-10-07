from __future__ import annotations

from datetime import datetime
from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from yimba.modules.alerts.public import Alert
from yimba.modules.analysis.public import Emotion, SentimentLabel
from yimba.modules.identity.public import Role, TokenPair, User
from yimba.modules.mentions.application.ports import Counts, Stats
from yimba.modules.mentions.domain.model import Mention
from yimba.modules.watches.domain.model import ALLOWED_FREQUENCIES_MINUTES, Watch
from yimba.shared.pagination import Page
from yimba.shared.source import SourceKind

T = TypeVar("T")


class PageOut(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    size: int


def page_of(page: Page, convert) -> dict:
    return {"items": [convert(item) for item in page.items], "total": page.total, "page": page.page, "size": page.size}


# ---- watches ----------------------------------------------------------------------------------------------------


class WatchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    keywords: list[str] = Field(min_length=1, max_length=20)
    sources: list[SourceKind] = Field(min_length=1)
    languages: list[str] = ["fr"]
    countries: list[str] = ["CI"]
    frequency_minutes: int = Field(60, description=f"One of {ALLOWED_FREQUENCIES_MINUTES}")
    alert_negative_share: float = Field(0.4, gt=0, le=1)
    alert_min_mentions: int = Field(20, ge=1)


class WatchUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    keywords: list[str] | None = Field(None, min_length=1, max_length=20)
    sources: list[SourceKind] | None = Field(None, min_length=1)
    languages: list[str] | None = None
    countries: list[str] | None = None
    frequency_minutes: int | None = None
    alert_negative_share: float | None = Field(None, gt=0, le=1)
    alert_min_mentions: int | None = Field(None, ge=1)
    active: bool | None = None


class WatchOut(BaseModel):
    id: str
    name: str
    slug: str
    keywords: list[str]
    sources: list[SourceKind]
    languages: list[str]
    countries: list[str]
    frequency_minutes: int
    alert_negative_share: float
    alert_min_mentions: int
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, watch: Watch) -> "WatchOut":
        return cls(
            id=watch.id,
            name=watch.name,
            slug=watch.slug,
            keywords=list(watch.keywords),
            sources=list(watch.sources),
            languages=list(watch.languages),
            countries=list(watch.countries),
            frequency_minutes=watch.frequency.minutes,
            alert_negative_share=watch.threshold.negative_share,
            alert_min_mentions=watch.threshold.min_mentions,
            active=watch.active,
            created_at=watch.created_at,
            updated_at=watch.updated_at,
        )


# ---- mentions ---------------------------------------------------------------------------------------------------


class MentionOut(BaseModel):
    id: str
    source: SourceKind
    url: str | None
    text: str
    author_ref: str | None
    published_at: datetime
    language: str
    sentiment: SentimentLabel
    sentiment_scores: dict[str, float]
    emotion: Emotion | None
    likes: int
    shares: int
    views: int
    comments: int

    @classmethod
    def of(cls, mention: Mention) -> "MentionOut":
        return cls(
            id=mention.id,
            source=mention.source,
            url=mention.url,
            text=mention.text,
            author_ref=mention.author_ref,
            published_at=mention.published_at,
            language=mention.language,
            sentiment=mention.sentiment.label,
            sentiment_scores={
                "positive": round(mention.sentiment.positive, 4),
                "neutral": round(mention.sentiment.neutral, 4),
                "negative": round(mention.sentiment.negative, 4),
            },
            emotion=mention.emotion,
            likes=mention.metrics.likes,
            shares=mention.metrics.shares,
            views=mention.metrics.views,
            comments=mention.metrics.comments,
        )


class CountsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    positive: int
    neutral: int
    negative: int
    negative_share: float

    @classmethod
    def of(cls, counts: Counts) -> "CountsOut":
        return cls(
            total=counts.total,
            positive=counts.positive,
            neutral=counts.neutral,
            negative=counts.negative,
            negative_share=round(counts.negative_share, 4),
        )


class BucketOut(BaseModel):
    key: str
    counts: CountsOut


class StatsOut(BaseModel):
    totals: CountsOut
    buckets: list[BucketOut]
    emotions: dict[str, int]

    @classmethod
    def of(cls, stats: Stats) -> "StatsOut":
        return cls(
            totals=CountsOut.of(stats.totals),
            buckets=[BucketOut(key=b.key, counts=CountsOut.of(b.counts)) for b in stats.buckets],
            emotions=stats.emotions,
        )


# ---- alerts ----------------------------------------------------------------------------------------------


class AlertOut(BaseModel):
    id: str
    watch_id: str
    status: str
    message: str
    mentions: int
    negative: int
    negative_share: float
    threshold_share: float
    window_start: datetime
    window_end: datetime
    triggered_at: datetime
    acknowledged_at: datetime | None

    @classmethod
    def of(cls, alert: Alert) -> "AlertOut":
        return cls(
            id=alert.id,
            watch_id=alert.watch_id,
            status=alert.status.value,
            message=alert.message,
            mentions=alert.mentions,
            negative=alert.negative,
            negative_share=round(alert.negative_share, 4),
            threshold_share=alert.threshold_share,
            window_start=alert.window_start,
            window_end=alert.window_end,
            triggered_at=alert.triggered_at,
            acknowledged_at=alert.acknowledged_at,
        )


# ---- authentication and accounts -----------------------------------------------------------------------------------


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=1024, description="Length set by MIN_PASSWORD_LENGTH and MAX_PASSWORD_LENGTH")
    full_name: str | None = Field(None, max_length=200)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=1024)


class RefreshIn(BaseModel):
    refresh_token: str = Field(max_length=128)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=1024)
    new_password: str = Field(max_length=1024)


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    expires_in: int = Field(description="Lifetime of the access token, in seconds")
    refresh_token: str

    @classmethod
    def of(cls, pair: TokenPair) -> "TokenOut":
        return cls(
            access_token=pair.access_token,
            token_type=pair.token_type,
            expires_in=pair.expires_in,
            refresh_token=pair.refresh_token,
        )


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: Role
    active: bool
    created_at: datetime
    last_login_at: datetime | None
    deleted_at: datetime | None

    @classmethod
    def of(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            active=user.active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            deleted_at=user.deleted_at,
        )


class UserUpdateIn(BaseModel):
    role: Role | None = None
    active: bool | None = None
