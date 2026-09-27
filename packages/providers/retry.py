"""Deterministic retry behavior for provider calls."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .errors import ProviderRateLimitError, ProviderTimeoutError


def call_with_retry(
    func: Callable[[], Any],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    retryable: tuple[type[BaseException], ...] = (
        ProviderTimeoutError,
        ProviderRateLimitError,
    ),
    sleep: Callable[[float], Any] = time.sleep,
) -> Any:
    """Call ``func``, retrying selected provider failures with exponential backoff."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    for attempt in range(max_attempts):
        try:
            return func()
        except retryable:
            if attempt == max_attempts - 1:
                raise
            sleep(base_delay * (2**attempt))

    raise RuntimeError("unreachable")
