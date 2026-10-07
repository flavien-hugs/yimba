from __future__ import annotations

from typing import Any, Callable

from yimba.modules.analysis.domain.model import Sentiment

DEFAULT_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"


def _load_pipeline(model_name: str) -> Callable[..., Any]:
    try:
        from transformers import pipeline  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on the optional extra
        raise RuntimeError("Install the 'ml' extra to use the transformers sentiment analyzer") from exc
    return pipeline("text-classification", model=model_name, top_k=None, truncation=True, max_length=256)


class TransformersSentimentAnalyzer:
    """Multilingual sentiment model (XLM-RoBERTa family). Loaded lazily on first use.

    Fine-tune on an annotated French / nouchi corpus before relying on it for decisions.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        pipeline_factory: Callable[[str], Callable[..., Any]] = _load_pipeline,
    ) -> None:
        self._model_name = model_name
        self._factory = pipeline_factory
        self._pipeline: Callable[..., Any] | None = None

    def analyze(self, text: str, language: str) -> Sentiment:
        if self._pipeline is None:
            self._pipeline = self._factory(self._model_name)
        result = self._pipeline(text)
        rows = result[0] if result and isinstance(result[0], list) else result
        scores = {str(row["label"]).lower(): float(row["score"]) for row in rows}
        positive = scores.get("positive", 0.0)
        negative = scores.get("negative", 0.0)
        neutral = scores.get("neutral", max(0.0, 1.0 - positive - negative))
        total = positive + neutral + negative or 1.0
        return Sentiment(positive=positive / total, neutral=neutral / total, negative=negative / total)
