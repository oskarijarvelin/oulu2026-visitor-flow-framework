"""Oulu2026 Visitor Flow Framework, ingest package.

Fetches visitor, weather and traffic data from the configured upstream APIs,
normalizes it onto the shared time zone contract and writes the canonical
tables described in ``docs/FRAMEWORK_PLAN.md`` chapter 4.2.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any, Literal, TextIO

__version__ = "1.0.0"

__all__ = ["LogLevel", "__version__", "log_event", "set_log_level", "set_log_stream"]

LogLevel = Literal["debug", "info", "warning", "error"]

_LEVEL_ORDER: dict[str, int] = {"debug": 10, "info": 20, "warning": 30, "error": 40}
_min_level = "info"
_stream: TextIO | None = None


def set_log_level(level: LogLevel) -> None:
    """Set the minimum level that :func:`log_event` emits."""
    global _min_level
    _min_level = level


def set_log_stream(stream: TextIO | None) -> None:
    """Override the log destination. ``None`` restores stdout."""
    global _stream
    _stream = stream


def log_event(level: LogLevel, source: str, message: str, **fields: Any) -> None:
    """Write one structured log line (level, timestamp, source, message) to stdout."""
    if _LEVEL_ORDER[level] < _LEVEL_ORDER[_min_level]:
        return
    record: dict[str, Any] = {
        "level": level,
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "message": message,
    }
    record.update(fields)
    stream = _stream if _stream is not None else sys.stdout
    stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    stream.flush()
