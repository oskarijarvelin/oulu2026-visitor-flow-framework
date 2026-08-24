"""Fixtures for the forecast tests. The data generators live in :mod:`synthetic`."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from ovf_forecast import set_log_stream
from synthetic import REAL_REPO_ROOT, write_repo


@pytest.fixture(autouse=True)
def _quiet_logs() -> Iterator[None]:
    """Keep structured log output out of the test report."""
    set_log_stream(None)
    yield
    set_log_stream(None)


@pytest.fixture
def synthetic_repo(tmp_path: Path) -> Path:
    """A throwaway repository root holding a complete synthetic ``data/processed``."""
    return write_repo(tmp_path)


@pytest.fixture(scope="module")
def synthetic_repo_module(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The same fixture, built once per module.

    An end-to-end run costs a full backtest, so the tests that only read its output
    share one instead of paying for it eleven times over.
    """
    return write_repo(tmp_path_factory.mktemp("repo"))


@pytest.fixture(scope="module")
def real_repo() -> Path:
    """The repository itself, for the tests that check the shipped data end to end."""
    if not (REAL_REPO_ROOT / "data" / "processed" / "visitors_daily.csv").is_file():
        pytest.skip("data/processed is not populated")
    return REAL_REPO_ROOT
