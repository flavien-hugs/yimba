from __future__ import annotations

from typing import Mapping


class MlflowTracker:
    """Experiment tracking on a self-hosted MLflow server (needs the 'tracking' extra: mlflow-skinny)."""

    def __init__(self, tracking_uri: str, experiment: str = "yimba-analysis") -> None:
        try:
            import mlflow  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - depends on the optional extra
            raise RuntimeError("Install the 'tracking' extra to log evaluations to MLflow") from exc
        self._mlflow = mlflow
        self._tracking_uri = tracking_uri
        self._experiment = experiment

    def log_evaluation(
        self, run_name: str, params: Mapping[str, str], metrics: Mapping[str, float], artifacts: Mapping[str, str]
    ) -> str | None:
        mlflow = self._mlflow
        mlflow.set_tracking_uri(self._tracking_uri)
        mlflow.set_experiment(self._experiment)
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params(dict(params))
            mlflow.log_metrics(dict(metrics))
            for name, content in artifacts.items():
                mlflow.log_text(content, name)
        return run.info.run_id
