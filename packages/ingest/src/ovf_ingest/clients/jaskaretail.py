"""Jaskaretail IoT visitor counting client.

``POST /ext/sensor/visitor`` with the query in the URL, HTTP Basic auth, and one
request per counting direction. The response is a flat ``result`` list of
``{categoryName, locationId, visitors}`` rows in naive local time.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import requests

from .. import log_event
from ..config import AppConfig, VenueConfig
from . import request_json

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


class JaskaretailClient:
    """Fetches raw visitor payloads for one venue and counting direction."""

    def __init__(self, config: AppConfig, session: requests.Session | None = None) -> None:
        """Bind the client to a configuration and an optional shared session."""
        self.config = config
        self.source = config.sources.visitors
        self.http = config.sources.http
        self.session = session or requests.Session()

    def fetch(
        self,
        venue: VenueConfig,
        first_day: date,
        last_day: date,
        counting_type: str,
    ) -> dict[str, Any]:
        """Fetch one counting direction for an inclusive day window."""
        params = {
            "locationHierarchyIdList": str(venue.location_hierarchy_id),
            "startDate": first_day.isoformat(),
            "endDate": last_day.isoformat(),
            "interval": self.source.interval,
            "countingTypeId": counting_type,
        }
        description = (
            f"jaskaretail venue {venue.venue_id} {counting_type} "
            f"{first_day.isoformat()}..{last_day.isoformat()}"
        )
        log_event(
            "info",
            self.source.name,
            "Fetching visitor counts",
            venue_id=venue.venue_id,
            counting_type=counting_type,
            start=first_day.isoformat(),
            end=last_day.isoformat(),
        )
        username, password = self.config.visitor_credentials
        payload = request_json(
            lambda: self.session.post(
                self.source.api_url,
                params=params,
                headers=HEADERS,
                auth=(username, password),
                timeout=self.http.timeout_seconds,
            ),
            self.http,
            source=self.source.name,
            description=description,
        )
        rows = payload.get("result")
        log_event(
            "info",
            self.source.name,
            "Received visitor counts",
            venue_id=venue.venue_id,
            counting_type=counting_type,
            rows=len(rows) if isinstance(rows, list) else 0,
        )
        return payload
