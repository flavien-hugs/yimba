"""Label Studio (Community edition, self-hosted): the labeling interface, the tasks we send, the annotations we read.

Annotators see French labels; the codes used by Yimba are mapped here, in both directions.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from yimba.modules.analysis.application.evaluation import NO_EMOTION, AnnotatedText
from yimba.modules.analysis.domain.model import TextAnalysis

SENTIMENT_CHOICES = {"Positif": "positive", "Neutre": "neutral", "Négatif": "negative"}
EMOTION_CHOICES = {
    "Joie": "joy",
    "Colère": "anger",
    "Peur": "fear",
    "Tristesse": "sadness",
    "Confiance": "trust",
    "Aucune": NO_EMOTION,
}
LANGUAGE_CHOICES = {"Français": "fr", "Nouchi": "nouchi", "Anglais": "en", "Autre": "other"}


def _choices(name: str, choices: Iterable[str], *, required: bool = False) -> str:
    options = "\n".join(f'    <Choice value="{value}"/>' for value in choices)
    flag = ' required="true"' if required else ""
    return f'  <Choices name="{name}" toName="text" choice="single" showInline="true"{flag}>\n{options}\n  </Choices>'


LABELING_CONFIG = "\n".join(
    [
        "<View>",
        '  <Header value="Publication"/>',
        '  <Text name="text" value="$text"/>',
        '  <Header value="Sentiment exprimé envers le sujet"/>',
        _choices("sentiment", SENTIMENT_CHOICES, required=True),
        '  <Header value="Émotion dominante"/>',
        _choices("emotion", EMOTION_CHOICES),
        '  <Header value="Langue"/>',
        _choices("language", LANGUAGE_CHOICES),
        "</View>",
    ]
)

_FRENCH_SENTIMENT = {code: label for label, code in SENTIMENT_CHOICES.items()}
_FRENCH_EMOTION = {code: label for label, code in EMOTION_CHOICES.items()}


def build_tasks(
    texts: Sequence[Mapping[str, Any]], predictions: Sequence[TextAnalysis] | None = None, model_version: str = ""
) -> list[dict[str, Any]]:
    """Label Studio import format. ``texts`` items carry ``text`` and any metadata (mention id, source...).

    Predictions pre-fill the form: faster, but annotators tend to accept them. Leave them out to build a reference
    corpus.
    """
    tasks = []
    for index, data in enumerate(texts):
        task: dict[str, Any] = {"data": dict(data)}
        if predictions is not None:
            analysis = predictions[index]
            result = [_choice("sentiment", _FRENCH_SENTIMENT[analysis.sentiment.label.value])]
            result.append(
                _choice("emotion", _FRENCH_EMOTION[analysis.emotion.value if analysis.emotion else NO_EMOTION])
            )
            task["predictions"] = [{"model_version": model_version, "result": result}]
        tasks.append(task)
    return tasks


def _choice(name: str, value: str) -> dict[str, Any]:
    return {"from_name": name, "to_name": "text", "type": "choices", "value": {"choices": [value]}}


def read_annotations(export: Sequence[Mapping[str, Any]]) -> list[AnnotatedText]:
    """Read a Label Studio JSON export. Uses the most recent annotation that was not skipped."""
    corpus = []
    for task in export:
        annotations = [a for a in task.get("annotations") or [] if not a.get("was_cancelled")]
        if not annotations:
            continue
        latest = max(annotations, key=lambda a: str(a.get("updated_at") or a.get("created_at") or ""))
        answers = {
            item.get("from_name"): (item.get("value") or {}).get("choices", [None])[0]
            for item in latest.get("result") or []
            if item.get("type") == "choices"
        }
        data = task.get("data") or {}
        corpus.append(
            AnnotatedText(
                text=str(data.get("text") or ""),
                sentiment=SENTIMENT_CHOICES.get(answers.get("sentiment") or ""),
                emotion=EMOTION_CHOICES.get(answers.get("emotion") or ""),
                reference=str(data["mention_id"]) if data.get("mention_id") else None,
            )
        )
    return [item for item in corpus if item.text]
