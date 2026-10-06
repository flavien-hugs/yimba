"""The only import surface other modules may use."""

from yimba.modules.analysis.adapters.factory import build_text_analyzer
from yimba.modules.analysis.application.ports import TextAnalyzer
from yimba.modules.analysis.domain.model import Emotion, Sentiment, SentimentLabel, TextAnalysis

__all__ = ["Emotion", "Sentiment", "SentimentLabel", "TextAnalysis", "TextAnalyzer", "build_text_analyzer"]
