from __future__ import annotations

from functools import lru_cache

from yimba.modules.analysis.adapters.lexicon import (
    LexiconEmotionClassifier,
    LexiconSentimentAnalyzer,
    StopwordLanguageDetector,
)
from yimba.modules.analysis.application.ports import SentimentAnalyzer, TextAnalyzer
from yimba.modules.analysis.application.service import AnalysisService


@lru_cache(maxsize=4)
def build_text_analyzer(engine: str = "lexicon", model_name: str | None = None) -> TextAnalyzer:
    """One analyzer per process and configuration: a transformers model is loaded once, not on every task."""
    sentiment: SentimentAnalyzer
    if engine == "lexicon":
        sentiment = LexiconSentimentAnalyzer()
    elif engine == "transformers":
        from yimba.modules.analysis.adapters.transformers_sentiment import DEFAULT_MODEL, TransformersSentimentAnalyzer

        sentiment = TransformersSentimentAnalyzer(model_name or DEFAULT_MODEL)
    else:
        raise ValueError(f"Unknown analysis engine: {engine!r}")
    return AnalysisService(StopwordLanguageDetector(), sentiment, LexiconEmotionClassifier())
