"""Measure an analyzer against human annotations: the only way to know whether its numbers can inform a decision."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Mapping, Sequence

from yimba.modules.analysis.application.ports import ExperimentTracker, TextAnalyzer
from yimba.modules.analysis.domain.model import Emotion, SentimentLabel

NO_EMOTION = "none"
SENTIMENT_LABELS = tuple(label.value for label in SentimentLabel)
EMOTION_LABELS = (*(emotion.value for emotion in Emotion), NO_EMOTION)


@dataclass(frozen=True, slots=True)
class AnnotatedText:
    """One text and what a human said about it (``None`` when the annotator left that question blank)."""

    text: str
    sentiment: str | None = None
    emotion: str | None = None
    reference: str | None = None


@dataclass(frozen=True, slots=True)
class LabelScores:
    precision: float
    recall: float
    f1: float
    support: int


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    task: str
    size: int
    accuracy: float
    macro_f1: float
    per_label: Mapping[str, LabelScores]
    confusion: Mapping[str, Mapping[str, int]]  # gold label -> predicted label -> count
    errors: Sequence[Mapping[str, str | None]] = field(default_factory=tuple)

    def metrics(self) -> dict[str, float]:
        flat = {f"{self.task}_accuracy": self.accuracy, f"{self.task}_macro_f1": self.macro_f1}
        flat.update({f"{self.task}_f1_{label}": scores.f1 for label, scores in self.per_label.items()})
        return flat

    def confusion_csv(self) -> str:
        labels = list(self.confusion)
        lines = ["gold\\predicted," + ",".join(labels)]
        lines += [
            f"{gold}," + ",".join(str(self.confusion[gold][predicted]) for predicted in labels) for gold in labels
        ]
        return "\n".join(lines) + "\n"


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def score(task: str, gold: Sequence[str], predicted: Sequence[str], labels: Sequence[str]) -> EvaluationReport:
    if len(gold) != len(predicted):
        raise ValueError("gold and predicted must have the same length")
    confusion = {g: {p: 0 for p in labels} for g in labels}
    for g, p in zip(gold, predicted):
        confusion[g][p] += 1

    per_label: dict[str, LabelScores] = {}
    for label in labels:
        true_positives = confusion[label][label]
        predicted_as = sum(confusion[g][label] for g in labels)
        support = sum(confusion[label].values())
        precision, recall = _ratio(true_positives, predicted_as), _ratio(true_positives, support)
        f1 = _ratio(2 * true_positives, predicted_as + support)
        per_label[label] = LabelScores(precision, recall, f1, support)

    # Labels nobody used (neither the annotators nor the model) would only dilute the macro average.
    used = [label for label in labels if per_label[label].support or sum(confusion[g][label] for g in labels)]
    correct = sum(confusion[label][label] for label in labels)
    return EvaluationReport(
        task=task,
        size=len(gold),
        accuracy=_ratio(correct, len(gold)),
        macro_f1=sum(per_label[label].f1 for label in used) / len(used) if used else 0.0,
        per_label=per_label,
        confusion=confusion,
    )


class EvaluateAnalyzer:
    """Run the analyzer on an annotated corpus, score each task and record the run with the tracker."""

    def __init__(self, analyzer: TextAnalyzer, tracker: ExperimentTracker | None = None) -> None:
        self._analyzer = analyzer
        self._tracker = tracker

    def execute(
        self, corpus: Sequence[AnnotatedText], *, run_name: str, params: Mapping[str, str]
    ) -> tuple[list[EvaluationReport], str | None]:
        analyses = [self._analyzer.analyze(item.text) for item in corpus]
        reports: list[EvaluationReport] = []

        sentiment = [(item, a.sentiment.label.value) for item, a in zip(corpus, analyses) if item.sentiment]
        if sentiment:
            reports.append(self._report("sentiment", sentiment, lambda item: item.sentiment, SENTIMENT_LABELS))
        emotion = [
            (item, a.emotion.value if a.emotion else NO_EMOTION) for item, a in zip(corpus, analyses) if item.emotion
        ]
        if emotion:
            reports.append(self._report("emotion", emotion, lambda item: item.emotion, EMOTION_LABELS))

        run_id = None
        if self._tracker is not None and reports:
            metrics: dict[str, float] = {"corpus_size": float(len(corpus))}
            artifacts: dict[str, str] = {}
            for report in reports:
                metrics.update(report.metrics())
                artifacts[f"{report.task}_confusion.csv"] = report.confusion_csv()
                artifacts[f"{report.task}_errors.jsonl"] = "".join(
                    json.dumps(error, ensure_ascii=False) + "\n" for error in report.errors
                )
            run_id = self._tracker.log_evaluation(run_name, params, metrics, artifacts)
        return reports, run_id

    @staticmethod
    def _report(task, pairs, gold_of, labels) -> EvaluationReport:
        gold = [gold_of(item) for item, _ in pairs]
        predicted = [prediction for _, prediction in pairs]
        unknown = sorted(set(gold) - set(labels))
        if unknown:
            raise ValueError(f"unknown {task} labels in the annotations: {unknown}")
        errors = tuple(
            {"reference": item.reference, "text": item.text, "gold": g, "predicted": p}
            for (item, p), g in zip(pairs, gold)
            if g != p
        )
        return replace(score(task, gold, predicted, labels), errors=errors)
