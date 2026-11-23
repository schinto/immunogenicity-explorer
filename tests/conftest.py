"""Gemeinsame Test-Fixtures.

Tests laufen ohne Netz. Die CSV-Auszüge unter tests/fixtures/ stammen aus dem
öffentlichen IDC-Datensatz (CC BY 4.0), siehe DATA.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_dir() -> Path:
    """Verzeichnis mit den CSV-Auszügen für Tests."""
    return FIXTURE_DIR


@pytest.fixture
def cohorts_csv() -> Path:
    """Auszug aus clinical_trials.csv: 33 Zeilen, davon 30 mit ADA-Messwert."""
    return FIXTURE_DIR / "clinical_trials.sample.csv"


@pytest.fixture
def therapeutics_csv() -> Path:
    """Auszug aus therapeutics.csv, passend zu den Wirkstoffen in cohorts_csv."""
    return FIXTURE_DIR / "therapeutics.sample.csv"
