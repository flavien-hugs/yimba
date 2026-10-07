from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique

UNDETERMINED_LANGUAGE = "und"


@unique
class SentimentLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@unique
class Emotion(StrEnum):
    JOY = "joy"
    ANGER = "anger"
    FEAR = "fear"
    SADNESS = "sadness"
    TRUST = "trust"


@dataclass(frozen=True, slots=True)
class Sentiment:
    """Probability-like scores in [0, 1]; the three values sum to ~1."""

    positive: float
    neutral: float
    negative: float

    def __post_init__(self) -> None:
        for value in (self.positive, self.neutral, self.negative):
            if not 0.0 <= value <= 1.0:
                raise ValueError("sentiment scores must be in [0, 1]")
        if abs(self.positive + self.neutral + self.negative - 1.0) > 1e-3:
            raise ValueError("sentiment scores must sum to 1")

    @property
    def label(self) -> SentimentLabel:
        best = max(
            (self.positive, SentimentLabel.POSITIVE),
            (self.negative, SentimentLabel.NEGATIVE),
            (self.neutral, SentimentLabel.NEUTRAL),
            key=lambda pair: pair[0],
        )
        return best[1]

    @property
    def compound(self) -> float:
        return self.positive - self.negative

    @classmethod
    def neutral_only(cls) -> "Sentiment":
        return cls(positive=0.0, neutral=1.0, negative=0.0)


@dataclass(frozen=True, slots=True)
class TextAnalysis:
    language: str
    sentiment: Sentiment
    emotion: Emotion | None = None
