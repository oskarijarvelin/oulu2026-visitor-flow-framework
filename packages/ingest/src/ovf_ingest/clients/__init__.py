"""HTTP clients for the three upstream APIs, plus their shared retry policy."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import requests

from .. import log_event
from ..config import HttpConfig

__all__ = ["TransientHttpError", "request_json", "request_with_retry"]

RETRYABLE_STATUS_FLOOR = 500


class TransientHttpError(RuntimeError):
    """Raised when a request failed in a way that is worth retrying."""


def request_with_retry(
    call: Callable[[], requests.Response],
    http: HttpConfig,
    *,
    source: str,
    description: str,
) -> requests.Response:
    """Run an HTTP call with the configured retry policy.

    Retries HTTP 5xx and timeouts (and other transport errors) on an exponential
    backoff. HTTP 4xx is a client mistake and is never retried.
    """
    last_error: Exception | None = None
    for attempt in range(1, http.max_attempts + 1):
        try:
            response = call()
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
        else:
            if response.status_code < RETRYABLE_STATUS_FLOOR:
                response.raise_for_status()
                return response
            last_error = TransientHttpError(f"HTTP {response.status_code} from {description}")
        if attempt >= http.max_attempts:
            break
        delay = http.backoff_seconds[min(attempt - 1, len(http.backoff_seconds) - 1)]
        log_event(
            "warning",
            source,
            "Request failed, retrying",
            description=description,
            attempt=attempt,
            max_attempts=http.max_attempts,
            retry_in_seconds=delay,
            error=str(last_error),
        )
        time.sleep(delay)
    raise TransientHttpError(f"{description} failed after {http.max_attempts} attempts: {last_error}")


def request_json(
    call: Callable[[], requests.Response],
    http: HttpConfig,
    *,
    source: str,
    description: str,
) -> dict[str, Any]:
    """Run an HTTP call with retries and decode the JSON object it returns."""
    response = request_with_retry(call, http, source=source, description=description)
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"{description} returned a non-object JSON response")
    return payload
