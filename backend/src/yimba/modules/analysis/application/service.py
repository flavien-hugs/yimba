from __future__ import annotations

from yimba.modules.analysis.application.ports import EmotionClassifier, LanguageDetector, SentimentAnalyzer
from yimba.modules.analysis.domain.model import Sentiment, TextAnalysis


class AnalysisService:
    """Composes the three analysis ports behind the ``TextAnalyzer`` interface."""

    def __init__(
        self,
        language_detector: LanguageDetector,
        sentiment_analyzer: SentimentAnalyzer,
        emotion_classifier: EmotionClassifier,
    ) -> None:
        self._language = language_detector
        self._sentiment = sentiment_analyzer
        self._emotion = emotion_classifier

    def analyze(self, text: str) -> TextAnalysis:
        cleaned = (text or "").strip()
        if not cleaned:
            return TextAnalysis(language="und", sentiment=Sentiment.neutral_only(), emotion=None)
        language = self._language.detect(cleaned)
        return TextAnalysis(
            language=language,
            sentiment=self._sentiment.analyze(cleaned, language),
            emotion=self._emotion.classify(cleaned, language),
        )
