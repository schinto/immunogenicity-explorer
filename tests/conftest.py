"""Shared test fixtures.

Tests run without network. The CSV excerpts under tests/fixtures/ come from the
public IDC dataset (CC BY 4.0), see DATA.md.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from ida.app import reset_cohorts_cache
from ida.models import Cohort

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Point `IDA_DATA_DIR` at a directory without data and empty the cache.

    A test that forgets its dependency override fails with 503 instead of
    silently reading `data/idc/`, see the data access contract of spec 001.
    """
    monkeypatch.setenv("IDA_DATA_DIR", str(tmp_path / "no-data"))
    reset_cohorts_cache()
    yield
    reset_cohorts_cache()


@pytest.fixture
def make_cohort() -> Callable[..., Cohort]:
    """Build synthetic cohorts; every field can be overridden."""

    def _make_cohort(**overrides: object) -> Cohort:
        values: dict[str, object] = {
            "row_id": "CT9999_A1_001",
            "trial_id": "CT9999",
            "inn_name": "Testmab",
            "indication_category": "Healthy volunteers",
            "route": "Subcutaneous",
            "n_analyzed": 100,
            "n_ada_positive": 5,
            "ada_frequency_percent": 5.0,
        }
        values.update(overrides)
        return Cohort(**values)  # type: ignore[arg-type]

    return _make_cohort


@pytest.fixture
def fixture_dir() -> Path:
    """Directory with the CSV excerpts for tests."""
    return FIXTURE_DIR


@pytest.fixture
def cohorts_csv() -> Path:
    """Excerpt from clinical_trials.csv: 33 rows, 30 of them with an ADA measurement."""
    return FIXTURE_DIR / "clinical_trials.sample.csv"


@pytest.fixture
def therapeutics_csv() -> Path:
    """Excerpt from therapeutics.csv, matching the active substances in cohorts_csv."""
    return FIXTURE_DIR / "therapeutics.sample.csv"
