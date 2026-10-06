from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

from yimba.modules.analysis.public import Emotion, Sentiment, SentimentLabel
from yimba.shared.source import SourceKind

_URL = re.compile(r"https?://\S+")
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Metrics:
    likes: int = 0
    shares: int = 0
    views: int = 0
    comments: int = 0


def content_hash(text: str) -> str:
    """Fingerprint used to drop copies of the same text (reposts, scraper overlaps)."""
    normalized = _SPACES.sub(" ", _URL.sub("", text.lower())).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def anonymize_author(handle: str | None, salt: str) -> str | None:
    """Authors are stored as a salted hash: enough to count distinct voices, not to identify them."""
    if not handle:
        return None
    return hashlib.sha256(f"{salt}:{handle.strip().lower()}".encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class Mention:
    id: str
    watch_id: str
    source: SourceKind
    external_id: str
    text: str
    content_hash: str
    author_ref: str | None
    url: str | None
    published_at: datetime
    collected_at: datetime
    metrics: Metrics
    language: str
    sentiment: Sentiment
    emotion: Emotion | None

    @property
    def sentiment_label(self) -> SentimentLabel:
        return self.sentiment.label
