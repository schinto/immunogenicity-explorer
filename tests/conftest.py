"""Shared test fixtures.

Tests run without network. The CSV excerpts under tests/fixtures/ come from the
public IDC dataset (CC BY 4.0), see DATA.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


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
