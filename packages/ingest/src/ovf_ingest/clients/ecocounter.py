"""Oulun liikenne Eco-Counter GraphQL client.

One ``ecoCounterSiteData`` query per sensor. ``domain`` and ``step`` are GraphQL
enums and must be inlined without quotes; ``id``, ``begin`` and ``end`` are strings.
The endpoint interprets ``begin``/``end`` as UTC and answers in UTC.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

import requests

from .. import log_event
from ..config import AppConfig, SiteConfig
from . import request_json

GRAPHQL_ENUM_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
HEADERS = {"Content-Type": "application/json"}


def validate_enum(name: str, value: str) -> str:
    """Reject anything that cannot be safely inlined as a GraphQL enum."""
    if not GRAPHQL_ENUM_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid GraphQL enum value for {name}: {value}")
    return value


def build_site_data_query(sensor_id: str, domain: str, step: str, begin: str, end: str) -> str:
    """Build the site data query for one sensor."""
    return (
        "query GetEcoCounterSiteData { "
        "ecoCounterSiteData("
        f"id: {json.dumps(sensor_id)}, "
        f"domain: {validate_enum('domain', domain)}, "
        f"step: {validate_enum('step', step)}, "
        f"begin: {json.dumps(begin)}, "
        f"end: {json.dumps(end)}"
        ") { date counts } }"
    )


class EcoCounterClient:
    """Fetches raw Eco-Counter payloads for one site's sensors."""

    def __init__(self, config: AppConfig, session: requests.Session | None = None) -> None:
        """Bind the client to a configuration and an optional shared session."""
        self.config = config
        self.source = config.sources.traffic
        self.http = config.sources.http
        self.session = session or requests.Session()

    def fetch_sensor(
        self, site: SiteConfig, sensor_key: str, begin_utc: datetime, end_utc: datetime
    ) -> dict[str, Any]:
        """Fetch one sensor over a UTC instant window.

        The window bounds are formatted without an offset marker because the API
        rejects one; it already treats them as UTC.
        """
        sensor_id = site.sensors[sensor_key]
        begin = begin_utc.strftime("%Y-%m-%dT%H:%M:%S")
        end = end_utc.strftime("%Y-%m-%dT%H:%M:%S")
        query = build_site_data_query(sensor_id, site.domain, self.source.step, begin, end)
        description = f"eco-counter {site.site_id}/{sensor_key} {begin}..{end}"
        log_event(
            "info",
            self.source.name,
            "Fetching traffic counts",
            site_id=site.site_id,
            sensor=sensor_key,
            sensor_id=sensor_id,
            begin_utc=begin,
            end_utc=end,
        )
        payload = request_json(
            lambda: self.session.post(
                self.source.graphql_url,
                json={"query": query, "variables": None},
                headers=HEADERS,
                timeout=self.http.timeout_seconds,
            ),
            self.http,
            source=self.source.name,
            description=description,
        )
        errors = payload.get("errors")
        if errors:
            raise ValueError(f"{description} returned GraphQL errors: {errors}")
        return payload
