from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from yimba.modules.analysis.domain.model import UNDETERMINED_LANGUAGE, Emotion, Sentiment

_DATA = Path(__file__).parent / "data" / "lexicon.json"
_TOKEN = re.compile(r"[a-zà-ÿ']+", re.IGNORECASE)
_NEGATION_WINDOW = 3
_NEUTRAL_MASS = 0.5  # weight of "no opinion": one clear cue is enough to leave neutral


def _fold(token: str) -> str:
    return unicodedata.normalize("NFKD", token.lower()).encode("ascii", "ignore").decode("ascii")


def _tokens(text: str) -> list[str]:
    return [_fold(match.group(0).strip("'")) for match in _TOKEN.finditer(text)]


@lru_cache(maxsize=1)
def _lexicon() -> dict:
    raw = json.loads(_DATA.read_text(encoding="utf-8"))
    return {
        "positive": {_fold(w) for w in raw["positive"]},
        "negative": {_fold(w) for w in raw["negative"]},
        "emotions": {name: {_fold(w) for w in words} for name, words in raw["emotions"].items()},
        "positive_emojis": raw["positive_emojis"],
        "negative_emojis": raw["negative_emojis"],
        "negations": {_fold(w) for w in raw["negations"]},
        "stopwords": {lang: {_fold(w) for w in words} for lang, words in raw["stopwords"].items()},
    }


class StopwordLanguageDetector:
    """Cheap fr/en detector. Returns ``und`` rather than guessing on short or ambiguous text."""

    def detect(self, text: str) -> str:
        lexicon = _lexicon()
        tokens = _tokens(text)
        scores = {lang: sum(1 for token in tokens if token in words) for lang, words in lexicon["stopwords"].items()}
        best_lang, best = max(scores.items(), key=lambda item: item[1])
        others = [score for lang, score in scores.items() if lang != best_lang]
        if best == 0 or any(score == best for score in others):
            return UNDETERMINED_LANGUAGE
        return best_lang


class LexiconSentimentAnalyzer:
    """Baseline sentiment analyzer: lexicon + emojis + simple negation handling."""

    def analyze(self, text: str, language: str) -> Sentiment:
        lexicon = _lexicon()
        tokens = _tokens(text)
        positive = negative = 0.0

        for index, token in enumerate(tokens):
            if token in lexicon["positive"]:
                polarity = 1.0
            elif token in lexicon["negative"]:
                polarity = -1.0
            else:
                continue
            window = tokens[max(0, index - _NEGATION_WINDOW) : index]
            if any(previous in lexicon["negations"] for previous in window):
                polarity = -polarity * 0.8
            if polarity > 0:
                positive += polarity
            else:
                negative += -polarity

        positive += sum(text.count(emoji) for emoji in lexicon["positive_emojis"])
        negative += sum(text.count(emoji) for emoji in lexicon["negative_emojis"])

        total = positive + negative + _NEUTRAL_MASS
        pos, neg = positive / total, negative / total
        return Sentiment(positive=pos, neutral=max(0.0, 1.0 - pos - neg), negative=neg)


class LexiconEmotionClassifier:
    def classify(self, text: str, language: str) -> Emotion | None:
        emotions = _lexicon()["emotions"]
        tokens = set(_tokens(text))
        scored = {name: len(tokens & words) for name, words in emotions.items()}
        best_name, best = max(scored.items(), key=lambda item: item[1])
        if best == 0 or sum(1 for score in scored.values() if score == best) > 1:
            return None
        return Emotion(best_name)
