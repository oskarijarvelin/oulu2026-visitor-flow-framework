"""Open-Meteo weather client.

Two endpoints share one response shape: ``/v1/archive`` for history and
``/v1/forecast`` for today onwards (at most 16 forecast days). Both are queried
with ``timezone=Europe/Helsinki``, so ``hourly.time`` is naive local time.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import requests

from .. import log_event
from ..config import AppConfig
from . import request_json

ARCHIVE = "archive"
FORECAST = "forecast"
MAX_PAST_DAYS = 92


class OpenMeteoClient:
    """Fetches raw hourly weather payloads for one coordinate pair."""

    def __init__(self, config: AppConfig, session: requests.Session | None = None) -> None:
        """Bind the client to a configuration and an optional shared session."""
        self.config = config
        self.source = config.sources.weather
        self.http = config.sources.http
        self.timezone = config.sources.timezone
        self.session = session or requests.Session()

    def fetch_archive(
        self, latitude: float, longitude: float, first_day: date, last_day: date
    ) -> dict[str, Any]:
        """Fetch reanalysis history for an inclusive day window."""
        params: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": first_day.isoformat(),
            "end_date": last_day.isoformat(),
            "hourly": ",".join(self.source.hourly_variables),
            "timezone": self.timezone,
        }
        description = f"open-meteo archive {first_day.isoformat()}..{last_day.isoformat()}"
        log_event(
            "info",
            self.source.name,
            "Fetching weather archive",
            start=first_day.isoformat(),
            end=last_day.isoformat(),
            latitude=latitude,
            longitude=longitude,
        )
        return request_json(
            lambda: self.session.get(
                self.source.archive_url, params=params, timeout=self.http.timeout_seconds
            ),
            self.http,
            source=self.source.name,
            description=description,
        )

    def fetch_forecast(
        self, latitude: float, longitude: float, first_day: date, last_day: date, today: date
    ) -> dict[str, Any]:
        """Fetch the forecast window, optionally reaching back with ``past_days``.

        ``forecast_days`` counts from today and is capped at the documented 16.
        """
        past_days = max(0, min((today - first_day).days, MAX_PAST_DAYS))
        forecast_days = max(1, min((last_day - today).days + 1, self.source.max_forecast_days))
        params: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(self.source.hourly_variables),
            "forecast_days": forecast_days,
            "timezone": self.timezone,
        }
        if past_days:
            params["past_days"] = past_days
        description = f"open-meteo forecast {first_day.isoformat()}..{last_day.isoformat()}"
        log_event(
            "info",
            self.source.name,
            "Fetching weather forecast",
            start=first_day.isoformat(),
            end=last_day.isoformat(),
            past_days=past_days,
            forecast_days=forecast_days,
        )
        return request_json(
            lambda: self.session.get(
                self.source.forecast_url, params=params, timeout=self.http.timeout_seconds
            ),
            self.http,
            source=self.source.name,
            description=description,
        )

    def archive_cutoff(self, today: date) -> date:
        """Last day the archive endpoint can be expected to cover."""
        return today - timedelta(days=self.source.archive_lag_days)
