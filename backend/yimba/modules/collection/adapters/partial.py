from __future__ import annotations

import logging
from typing import Awaitable, Callable, Sequence, TypeVar

from yimba.modules.collection.domain.model import CollectedItem
from yimba.shared.errors import ExternalServiceError

logger = logging.getLogger(__name__)
T = TypeVar("T")


async def collect_partially(
    units: Sequence[T],
    fetch: Callable[[T], Awaitable[Sequence[CollectedItem]]],
    *,
    label: str,
    describe: Callable[[T], str] = str,
) -> list[CollectedItem]:
    """Fetch every unit (keyword, feed, provider...) and keep what succeeded.

    One failing unit must not throw away what the others already fetched; the collection only fails
    when every unit failed.
    """
    collected: list[CollectedItem] = []
    errors: list[ExternalServiceError] = []
    for unit in units:
        try:
            collected.extend(await fetch(unit))
        except ExternalServiceError as exc:
            errors.append(exc)
            logger.warning("%s: %s failed: %s", label, describe(unit), exc.message)
    if errors and len(errors) == len(units):
        raise errors[0]
    return collected
