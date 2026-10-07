from __future__ import annotations

import sentry_sdk

from yimba import __version__


def init_error_tracking(dsn: str | None, environment: str, component: str) -> bool:
    """Report unhandled errors and ERROR logs to GlitchTip (self-hosted, speaks the Sentry protocol).

    Does nothing without a DSN. The FastAPI and Celery integrations are enabled automatically.
    """
    if not dsn:
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=f"yimba@{__version__}",
        send_default_pii=False,
        traces_sample_rate=0.0,
    )
    sentry_sdk.set_tag("component", component)
    return True
