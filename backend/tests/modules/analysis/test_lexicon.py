import pytest

from yimba.modules.analysis.domain.model import Emotion, Sentiment, SentimentLabel
from yimba.modules.analysis.public import build_text_analyzer


@pytest.fixture
def analyzer():
    return build_text_analyzer("lexicon")


@pytest.mark.parametrize(
    ("text", "language", "label"),
    [
        ("Merci aux agents de santé, la campagne est très bien organisée 😊", "fr", SentimentLabel.POSITIVE),
        ("Rupture de doses, c'est la honte, aucune information", "fr", SentimentLabel.NEGATIVE),
        ("Le ministère annonce l'ouverture de 120 centres de vaccination", "fr", SentimentLabel.NEUTRAL),
        ("the vaccine is not good, I am angry", "en", SentimentLabel.NEGATIVE),
    ],
)
def test_language_and_sentiment(analyzer, text, language, label):
    result = analyzer.analyze(text)
    assert result.language == language
    assert result.sentiment.label is label


def test_negation_flips_polarity(analyzer):
    assert analyzer.analyze("ce n'est pas bon du tout").sentiment.label is SentimentLabel.NEGATIVE


def test_emotion_needs_a_clear_winner(analyzer):
    assert analyzer.analyze("j'ai peur, c'est dangereux").emotion is Emotion.FEAR
    assert analyzer.analyze("rien de particulier").emotion is None


def test_empty_text_is_neutral_and_undetermined(analyzer):
    result = analyzer.analyze("   ")
    assert result.language == "und"
    assert result.sentiment == Sentiment.neutral_only()


def test_scores_always_sum_to_one(analyzer):
    for text in ("super super super bien", "honte colère arnaque", "x"):
        s = analyzer.analyze(text).sentiment
        assert s.positive + s.neutral + s.negative == pytest.approx(1.0)


def test_sentiment_rejects_invalid_scores():
    with pytest.raises(ValueError):
        Sentiment(positive=0.9, neutral=0.9, negative=0.0)


def test_unknown_engine_is_rejected():
    with pytest.raises(ValueError):
        build_text_analyzer("magic")


def test_transformers_adapter_maps_model_output_without_loading_a_model():
    from yimba.modules.analysis.adapters.transformers_sentiment import TransformersSentimentAnalyzer

    def factory(_name):
        return lambda text: [
            [
                {"label": "negative", "score": 0.7},
                {"label": "neutral", "score": 0.2},
                {"label": "positive", "score": 0.1},
            ]
        ]

    sentiment = TransformersSentimentAnalyzer(pipeline_factory=factory).analyze("texte", "fr")
    assert sentiment.label is SentimentLabel.NEGATIVE
    assert sentiment.negative == pytest.approx(0.7)
