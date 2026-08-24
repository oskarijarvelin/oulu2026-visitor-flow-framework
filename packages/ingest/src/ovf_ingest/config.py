"""Pydantic models for the JSON configuration under ``config/``."""

from __future__ import annotations

import json
import os
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from . import log_event

ENV_FILE_NAMES = (".env", ".env.local")
ROOT_MARKERS = ("config/venues.json", "config/sources.json")


class VenueConfig(BaseModel):
    """One venue: coordinates for weather, hierarchy id for the visitor API."""

    model_config = ConfigDict(frozen=True)

    venue_id: int
    name: str
    city: str
    latitude: float
    longitude: float
    capacity: int
    location_hierarchy_id: int
    tickets_path: str


class SiteConfig(BaseModel):
    """One Eco-Counter measurement site and its four directional sensors."""

    model_config = ConfigDict(frozen=False)

    site_id: str
    name: str
    domain: str
    sensors: dict[str, str]


class HttpConfig(BaseModel):
    """Shared HTTP behaviour: timeout and the retry backoff schedule."""

    model_config = ConfigDict(frozen=True)

    timeout_seconds: float = 60.0
    max_attempts: int = 3
    backoff_seconds: tuple[float, ...] = (1.0, 4.0, 16.0)


class VisitorsSourceConfig(BaseModel):
    """Jaskaretail IoT visitor counting."""

    model_config = ConfigDict(frozen=True)

    name: str = "jaskaretail"
    api_url: str
    interval: str = "60min"
    counting_types: tuple[str, ...] = ("in", "out")
    raw_dir: str = "data/raw/visitors"
    username_env: str = "JASKARETAIL_BASIC_AUTH_USERNAME"
    password_env: str = "JASKARETAIL_BASIC_AUTH_PASSWORD"


class WeatherSourceConfig(BaseModel):
    """Open-Meteo archive and forecast endpoints."""

    model_config = ConfigDict(frozen=True)

    name: str = "open-meteo"
    archive_url: str
    forecast_url: str
    hourly_variables: tuple[str, ...]
    max_forecast_days: int = 16
    archive_lag_days: int = 6
    raw_dir: str = "data/raw/weather"


class TrafficSourceConfig(BaseModel):
    """Oulun liikenne Eco-Counter GraphQL endpoint."""

    model_config = ConfigDict(frozen=True)

    name: str = "eco-counter"
    graphql_url: str
    step: str = "hour"
    raw_dir: str = "data/raw/traffic"


class TicketsSourceConfig(BaseModel):
    """Manually maintained ticket sales CSV files."""

    model_config = ConfigDict(frozen=True)

    name: str = "tickets"
    raw_dir: str = "data/raw/tickets"


class CalendarSourceConfig(BaseModel):
    """Maintained holiday calendar."""

    model_config = ConfigDict(frozen=True)

    name: str = "calendar"
    holidays_path: str = "config/holidays.csv"


class QualityGateConfig(BaseModel):
    """Thresholds for the quality gates run before the canonical tables are written."""

    model_config = ConfigDict(frozen=True)

    max_visitor_gap_hours: int = 48
    visitor_gap_lookback_days: int = 30
    min_weather_coverage: float = 0.99
    daily_total_capacity_multiplier: int = 96


class ClimatologyConfig(BaseModel):
    """Where the long-term weather normals are written."""

    model_config = ConfigDict(frozen=True)

    output_dir: str = "data/reference/climatology"


class SourcesConfig(BaseModel):
    """Contents of ``config/sources.json``."""

    model_config = ConfigDict(frozen=True)

    timezone: str = "Europe/Helsinki"
    default_days_back: int = 7
    http: HttpConfig = Field(default_factory=HttpConfig)
    visitors: VisitorsSourceConfig
    weather: WeatherSourceConfig
    traffic: TrafficSourceConfig
    tickets: TicketsSourceConfig = Field(default_factory=TicketsSourceConfig)
    calendar: CalendarSourceConfig = Field(default_factory=CalendarSourceConfig)
    quality_gates: QualityGateConfig = Field(default_factory=QualityGateConfig)
    climatology: ClimatologyConfig = Field(default_factory=ClimatologyConfig)
    processed_dir: str = "data/processed"


class AppConfig(BaseModel):
    """Everything the pipeline needs, resolved against one repository root."""

    model_config = ConfigDict(frozen=False)

    root: Path
    venues: tuple[VenueConfig, ...]
    sites: tuple[SiteConfig, ...]
    sources: SourcesConfig

    def path(self, relative: str) -> Path:
        """Resolve a repository-relative path from the configuration."""
        candidate = Path(relative)
        return candidate if candidate.is_absolute() else self.root / candidate

    def venue(self, venue_id: int) -> VenueConfig:
        """Return one venue by id."""
        for venue in self.venues:
            if venue.venue_id == venue_id:
                return venue
        raise KeyError(f"Unknown venue_id: {venue_id}")

    def site(self, site_id: str) -> SiteConfig:
        """Return one Eco-Counter site by id."""
        for site in self.sites:
            if site.site_id == site_id:
                return site
        raise KeyError(f"Unknown site_id: {site_id}")

    def select_venues(self, venue_ids: tuple[int, ...] | None) -> tuple[VenueConfig, ...]:
        """Return the requested venues, or all of them when nothing is requested."""
        if not venue_ids:
            return self.venues
        return tuple(self.venue(venue_id) for venue_id in venue_ids)

    @cached_property
    def visitor_credentials(self) -> tuple[str, str]:
        """HTTP Basic credentials for the visitor API, from the environment or a .env file."""
        source = self.sources.visitors
        username = os.environ.get(source.username_env)
        password = os.environ.get(source.password_env)
        if not username or not password:
            file_values = read_env_files(self.root)
            username = username or file_values.get(source.username_env)
            password = password or file_values.get(source.password_env)
        if not username or not password:
            raise RuntimeError(
                f"Missing visitor API credentials. Set {source.username_env} and "
                f"{source.password_env} in the environment or in a repository-root .env file "
                "(see .env.example)."
            )
        return username, password


def find_repo_root(start: Path | None = None) -> Path:
    """Locate the repository root by walking up until the config files are found."""
    override = os.environ.get("OVF_ROOT")
    if override:
        return Path(override).resolve()
    candidates: list[Path] = []
    if start is not None:
        candidates.append(start.resolve())
    candidates.extend([Path.cwd().resolve(), Path(__file__).resolve()])
    for candidate in candidates:
        for directory in (candidate, *candidate.parents):
            if all((directory / marker).is_file() for marker in ROOT_MARKERS):
                return directory
    raise FileNotFoundError(
        "Could not locate the repository root. Run from inside the repository or set OVF_ROOT."
    )


def parse_env_text(text: str) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines, tolerating ``export`` prefixes and quoted values."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def read_env_files(root: Path) -> dict[str, str]:
    """Read repository-root .env files. Earlier files win over later ones."""
    values: dict[str, str] = {}
    for name in ENV_FILE_NAMES:
        path = root / name
        if not path.is_file():
            continue
        for key, value in parse_env_text(path.read_text(encoding="utf-8")).items():
            values.setdefault(key, value)
    return values


def load_config(root: Path | None = None) -> AppConfig:
    """Load ``config/venues.json``, ``config/sites.json`` and ``config/sources.json``."""
    resolved_root = find_repo_root(root)
    venues_raw = json.loads((resolved_root / "config" / "venues.json").read_text(encoding="utf-8"))
    sites_raw = json.loads((resolved_root / "config" / "sites.json").read_text(encoding="utf-8"))
    sources_raw = json.loads((resolved_root / "config" / "sources.json").read_text(encoding="utf-8"))
    config = AppConfig(
        root=resolved_root,
        venues=tuple(VenueConfig(**item) for item in venues_raw["venues"]),
        sites=tuple(SiteConfig(**item) for item in sites_raw["sites"]),
        sources=SourcesConfig(**sources_raw),
    )
    log_event(
        "debug",
        "config",
        "Loaded configuration",
        root=str(resolved_root),
        venues=[venue.venue_id for venue in config.venues],
        sites=[site.site_id for site in config.sites],
    )
    return config
