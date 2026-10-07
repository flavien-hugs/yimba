import sys
import types
import xml.etree.ElementTree as ElementTree

import pytest

from yimba.modules.analysis.adapters.label_studio import LABELING_CONFIG, build_tasks, read_annotations
from yimba.modules.analysis.adapters.mlflow_tracker import MlflowTracker
from yimba.modules.analysis.application.evaluation import AnnotatedText, EvaluateAnalyzer, score
from yimba.modules.analysis.public import build_text_analyzer


def test_score_computes_accuracy_macro_f1_and_confusion():
    gold = ["negative", "negative", "positive", "neutral"]
    predicted = ["negative", "positive", "positive", "neutral"]
    report = score("sentiment", gold, predicted, ["positive", "neutral", "negative"])

    assert report.accuracy == pytest.approx(0.75)
    assert report.per_label["negative"].precision == 1.0 and report.per_label["negative"].recall == 0.5
    assert report.per_label["positive"].f1 == pytest.approx(2 / 3)
    assert report.macro_f1 == pytest.approx((2 / 3 + 1 + 2 / 3) / 3)
    assert report.confusion["negative"]["positive"] == 1
    assert report.confusion_csv().splitlines()[0] == "gold\\predicted,positive,neutral,negative"


def test_unused_labels_do_not_dilute_the_macro_average():
    report = score("emotion", ["joy", "joy"], ["joy", "joy"], ["joy", "anger", "fear"])
    assert report.macro_f1 == 1.0


class Tracker:
    def __init__(self):
        self.runs = []

    def log_evaluation(self, run_name, params, metrics, artifacts):
        self.runs.append((run_name, dict(params), dict(metrics), dict(artifacts)))
        return "run-1"


def test_evaluate_scores_each_annotated_task_and_records_the_run():
    corpus = [
        AnnotatedText("Bravo, super campagne", sentiment="positive", emotion="joy", reference="m1"),
        AnnotatedText("Honte et scandale", sentiment="negative", emotion="anger", reference="m2"),
        AnnotatedText("Le ministre parle ce matin", sentiment="neutral", reference="m3"),
        AnnotatedText("Bravo mais quelle honte", sentiment="negative", reference="m4"),
    ]
    tracker = Tracker()
    reports, run_id = EvaluateAnalyzer(build_text_analyzer("lexicon"), tracker).execute(
        corpus, run_name="lexicon-test", params={"engine": "lexicon"}
    )

    sentiment, emotion = reports
    assert (sentiment.task, sentiment.size, emotion.task, emotion.size) == ("sentiment", 4, "emotion", 2)
    # The lexicon breaks the positive/negative tie of a mixed text towards positive: a known weakness.
    assert [e["reference"] for e in sentiment.errors] == ["m4"]
    ((name, params, metrics, artifacts),) = tracker.runs
    assert run_id == "run-1" and name == "lexicon-test" and params == {"engine": "lexicon"}
    assert metrics["sentiment_accuracy"] == 0.75 and metrics["corpus_size"] == 4.0
    assert set(artifacts) == {
        "sentiment_confusion.csv",
        "sentiment_errors.jsonl",
        "emotion_confusion.csv",
        "emotion_errors.jsonl",
    }
    assert '"m4"' in artifacts["sentiment_errors.jsonl"]


def test_unknown_annotation_labels_are_rejected():
    with pytest.raises(ValueError, match="unknown sentiment labels"):
        EvaluateAnalyzer(build_text_analyzer("lexicon")).execute(
            [AnnotatedText("texte", sentiment="mitigé")], run_name="x", params={}
        )


def test_labeling_config_is_valid_xml_with_the_three_questions():
    root = ElementTree.fromstring(LABELING_CONFIG)
    assert {c.get("name") for c in root.iter("Choices")} == {"sentiment", "emotion", "language"}
    assert [c.get("value") for c in root.iter("Choice")][:3] == ["Positif", "Neutre", "Négatif"]


def test_tasks_round_trip_through_a_label_studio_export():
    analyzer = build_text_analyzer("lexicon")
    texts = [{"text": "Honte et scandale", "mention_id": "m1"}, {"text": "Rien à signaler", "mention_id": "m2"}]
    tasks = build_tasks(texts, [analyzer.analyze(t["text"]) for t in texts], model_version="lexicon")
    assert tasks[0]["data"] == texts[0]
    assert tasks[0]["predictions"][0]["result"][0]["value"] == {"choices": ["Négatif"]}
    assert "predictions" not in build_tasks(texts)[0]

    def answer(sentiment, emotion=None, cancelled=False, updated="2026-10-06T10:00:00Z"):
        result = [{"from_name": "sentiment", "type": "choices", "value": {"choices": [sentiment]}}]
        if emotion:
            result.append({"from_name": "emotion", "type": "choices", "value": {"choices": [emotion]}})
        return {"result": result, "was_cancelled": cancelled, "updated_at": updated}

    export = [
        {
            "data": texts[0],
            "annotations": [answer("Neutre"), answer("Négatif", "Colère", updated="2026-10-06T11:00:00Z")],
        },
        {"data": texts[1], "annotations": [answer("Neutre", cancelled=True)]},
        {"data": {"text": "Sans réponse"}, "annotations": []},
    ]
    (item,) = read_annotations(export)
    assert (item.text, item.sentiment, item.emotion, item.reference) == ("Honte et scandale", "negative", "anger", "m1")


def test_mlflow_tracker_logs_params_metrics_and_files(monkeypatch):
    calls = []

    class Run:
        info = types.SimpleNamespace(run_id="abc")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    fake = types.SimpleNamespace(
        set_tracking_uri=lambda uri: calls.append(("uri", uri)),
        set_experiment=lambda name: calls.append(("experiment", name)),
        start_run=lambda run_name: calls.append(("run", run_name)) or Run(),
        log_params=lambda params: calls.append(("params", params)),
        log_metrics=lambda metrics: calls.append(("metrics", metrics)),
        log_text=lambda content, name: calls.append(("text", name)),
    )
    monkeypatch.setitem(sys.modules, "mlflow", fake)

    tracker = MlflowTracker("http://mlflow:5000", "yimba-analysis")
    assert tracker.log_evaluation("r", {"engine": "lexicon"}, {"acc": 0.5}, {"c.csv": "a,b"}) == "abc"
    assert calls == [
        ("uri", "http://mlflow:5000"),
        ("experiment", "yimba-analysis"),
        ("run", "r"),
        ("params", {"engine": "lexicon"}),
        ("metrics", {"acc": 0.5}),
        ("text", "c.csv"),
    ]


def test_analyzers_are_built_once_per_configuration():
    assert build_text_analyzer("lexicon") is build_text_analyzer("lexicon")
