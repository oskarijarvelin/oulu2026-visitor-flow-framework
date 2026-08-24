"""Offline stand-ins and helpers shared by the ingest tests.

These live outside ``conftest`` because both test packages in this repository have a
``conftest.py``, and a bare ``from conftest import ...`` would resolve to whichever of
the two landed on ``sys.path`` first.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar

from ovf_ingest.config import AppConfig, SiteConfig, VenueConfig
from ovf_ingest.normalize import local_midnight, tz_of

FIXTURE_DIR = Path(__file__).parent / "fixtures"
REPO_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"

TICKETS_CSV = """DATE,TICKETS,GROUPS,TOTAL
14.1.2026,16,370,386
15.1.2026,33,0,33
16.1.2026,158,0,158
"""
TICKETS_CSV_FINNISH = """pvm;liput;ryhmat;yhteensa
14.1.2026;16;370;386
15.1.2026;33;0;33
"""


def load_fixture(name: str) -> dict[str, Any]:
    """Load one captured API response."""
    payload: dict[str, Any] = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return payload


class FakeJaskaretail:
    """Answers with a deterministic 24-slot local day, like the real API does."""

    counts: ClassVar[dict[tuple[int, str, str], int]] = {}
    missing_days: ClassVar[set[date]] = set()
    fail_venues: ClassVar[set[int]] = set()

    def __init__(self, config: AppConfig, session: Any = None) -> None:
        self.config = config

    def fetch(
        self, venue: VenueConfig, first_day: date, last_day: date, counting_type: str
    ) -> dict[str, Any]:
        if venue.venue_id in self.fail_venues:
            raise RuntimeError(f"synthetic visitor outage for venue {venue.venue_id}")
        rows: list[dict[str, Any]] = []
        day = first_day
        while day <= last_day:
            if day not in self.missing_days:
                for hour in range(24):
                    stamp = f"{day.strftime('%d/%m/%Y')} {hour:02d}:00:00"
                    key = (venue.venue_id, counting_type, stamp)
                    rows.append(
                        {
                            "categoryName": stamp,
                            "locationId": venue.location_hierarchy_id,
                            "visitors": self.counts.get(key, hour),
                        }
                    )
            day += timedelta(days=1)
        return {"metadata": {"success": True}, "result": rows}


class FakeOpenMeteo:
    """Answers with the fixed-offset shape the real archive endpoint uses."""

    offset_seconds = 10800
    fail = False

    def __init__(self, config: AppConfig, session: Any = None) -> None:
        self.config = config
        self.variables = config.sources.weather.hourly_variables

    def archive_cutoff(self, today: date) -> date:
        return today - timedelta(days=self.config.sources.weather.archive_lag_days)

    def _payload(self, first_day: date, last_day: date) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("synthetic weather outage")
        times: list[str] = []
        day = first_day
        while day <= last_day:
            times.extend(f"{day.isoformat()}T{hour:02d}:00" for hour in range(24))
            day += timedelta(days=1)
        hourly: dict[str, Any] = {"time": times}
        for index, variable in enumerate(self.variables):
            hourly[variable] = [float(index + position % 5) for position in range(len(times))]
        return {
            "latitude": 65.0,
            "longitude": 25.5,
            "utc_offset_seconds": self.offset_seconds,
            "timezone": "Europe/Helsinki",
            "hourly_units": {"time": "iso8601"},
            "hourly": hourly,
        }

    def fetch_archive(
        self, latitude: float, longitude: float, first_day: date, last_day: date
    ) -> dict[str, Any]:
        return self._payload(first_day, last_day)

    def fetch_forecast(
        self, latitude: float, longitude: float, first_day: date, last_day: date, today: date
    ) -> dict[str, Any]:
        return self._payload(first_day, last_day)


class FakeEcoCounter:
    """Answers in UTC, inclusive of both window ends, like the real endpoint does."""

    fail = False

    def __init__(self, config: AppConfig, session: Any = None) -> None:
        self.config = config

    def fetch_sensor(
        self, site: SiteConfig, sensor_key: str, begin_utc: datetime, end_utc: datetime
    ) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("synthetic eco-counter outage")
        rows: list[dict[str, Any]] = []
        cursor = begin_utc
        while cursor <= end_utc:
            rows.append(
                {
                    "date": cursor.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "counts": cursor.hour + len(sensor_key),
                }
            )
            cursor += timedelta(hours=1)
        return {"data": {"ecoCounterSiteData": rows}}


def helsinki_midnight_utc(day: date) -> datetime:
    """Local midnight of a day, as a UTC instant."""
    return local_midnight(day, tz_of("Europe/Helsinki")).astimezone(UTC)
