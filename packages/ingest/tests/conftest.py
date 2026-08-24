"""Shared test fixtures. No test in this package touches the network.

The stand-in clients and plain helpers live in :mod:`support`; only fixtures stay here.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from ovf_ingest import set_log_stream
from ovf_ingest.config import AppConfig, load_config
from support import (
    REPO_CONFIG_DIR,
    TICKETS_CSV,
    FakeEcoCounter,
    FakeJaskaretail,
    FakeOpenMeteo,
)


@pytest.fixture(autouse=True)
def _quiet_logs(capsys: pytest.CaptureFixture[str]) -> Iterator[None]:
    """Keep structured log output out of the test report."""
    set_log_stream(None)
    yield
    set_log_stream(None)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway repository root with the real configuration files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    for name in ("venues.json", "sites.json", "sources.json", "holidays.csv"):
        shutil.copy(REPO_CONFIG_DIR / name, config_dir / name)
    for venue_id in (1, 2):
        tickets_dir = tmp_path / "data" / "raw" / "tickets" / f"venue_{venue_id}"
        tickets_dir.mkdir(parents=True)
        (tickets_dir / "tickets.csv").write_text(TICKETS_CSV, encoding="utf-8")
    return tmp_path


@pytest.fixture
def config(repo: Path) -> AppConfig:
    """Configuration bound to the throwaway repository root."""
    return load_config(repo)


@pytest.fixture
def fake_clients(monkeypatch: pytest.MonkeyPatch) -> type[FakeJaskaretail]:
    """Swap the real clients for offline stand-ins inside the CLI module."""
    from ovf_ingest import cli

    FakeJaskaretail.counts = {}
    FakeJaskaretail.missing_days = set()
    FakeJaskaretail.fail_venues = set()
    FakeOpenMeteo.fail = False
    FakeOpenMeteo.offset_seconds = 10800
    FakeEcoCounter.fail = False
    monkeypatch.setattr(cli, "JaskaretailClient", FakeJaskaretail)
    monkeypatch.setattr(cli, "OpenMeteoClient", FakeOpenMeteo)
    monkeypatch.setattr(cli, "EcoCounterClient", FakeEcoCounter)
    return FakeJaskaretail
