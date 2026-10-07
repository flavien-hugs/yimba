from __future__ import annotations

from typing import Mapping, Protocol

from yimba.modules.analysis.domain.model import Emotion, Sentiment, TextAnalysis


class LanguageDetector(Protocol):
    def detect(self, text: str) -> str:
        """Return an ISO 639-1 code, or ``und`` when unsure."""


class SentimentAnalyzer(Protocol):
    def analyze(self, text: str, language: str) -> Sentiment: ...


class EmotionClassifier(Protocol):
    def classify(self, text: str, language: str) -> Emotion | None: ...


class TextAnalyzer(Protocol):
    """What other modules depend on."""

    def analyze(self, text: str) -> TextAnalysis: ...


class ExperimentTracker(Protocol):
    """Records an evaluation run (parameters, metrics, files) and returns its id."""

    def log_evaluation(
        self, run_name: str, params: Mapping[str, str], metrics: Mapping[str, float], artifacts: Mapping[str, str]
    ) -> str | None: ...
