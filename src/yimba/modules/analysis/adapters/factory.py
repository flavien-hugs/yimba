from __future__ import annotations

from yimba.modules.analysis.adapters.lexicon import (
    LexiconEmotionClassifier,
    LexiconSentimentAnalyzer,
    StopwordLanguageDetector,
)
from yimba.modules.analysis.application.ports import SentimentAnalyzer, TextAnalyzer
from yimba.modules.analysis.application.service import AnalysisService


def build_text_analyzer(engine: str = "lexicon", model_name: str | None = None) -> TextAnalyzer:
    sentiment: SentimentAnalyzer
    if engine == "lexicon":
        sentiment = LexiconSentimentAnalyzer()
    elif engine == "transformers":
        from yimba.modules.analysis.adapters.transformers_sentiment import DEFAULT_MODEL, TransformersSentimentAnalyzer

        sentiment = TransformersSentimentAnalyzer(model_name or DEFAULT_MODEL)
    else:
        raise ValueError(f"Unknown analysis engine: {engine!r}")
    return AnalysisService(StopwordLanguageDetector(), sentiment, LexiconEmotionClassifier())
