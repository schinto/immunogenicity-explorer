"""Tests for loading cohorts from the IDC CSV (spec 001, AC1 to AC4)."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

from ida.data import load_cohorts
from ida.models import Cohort

# The columns used by the application, written exactly as in the dataset.
REQUIRED_COLUMNS = [
    "IDC Row identifier",
    "Trial ID",
    "Molecule Assessed for ADA INN Name",
    "Disease Indication Category",
    "Therapeutic Route of Administration",
    "Number of Patients analyzed for ADA",
    "Number of ADA+ patients",
    "Frequency of ADA+ patients",
]

NUMERIC_COLUMNS = [
    "Number of Patients analyzed for ADA",
    "Number of ADA+ patients",
    "Frequency of ADA+ patients",
]


def write_csv(path: Path, columns: list[str], rows: list[list[str]]) -> Path:
    """Write a small CSV with the given header and rows."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
    return path


def test_ac1_returns_only_cohorts_with_measured_ada_count(cohorts_csv: Path) -> None:
    """AC1: exactly the 30 rows with a value in `Number of Patients analyzed for ADA`."""
    cohorts = load_cohorts(cohorts_csv)

    assert len(cohorts) == 30
    assert all(cohort.n_analyzed is not None for cohort in cohorts)


def test_ac1_loader_keeps_line_breaks_inside_mapped_fields(tmp_path: Path) -> None:
    """AC1: a quoted line break in a mapped field does not split the record.

    The loader itself must handle the line break; the value is kept verbatim and
    the following record is still loaded at its own boundary.
    """
    multiline_name = "adalimumab\n(recombinant)"
    path = write_csv(
        tmp_path / "clinical_trials.csv",
        REQUIRED_COLUMNS,
        [
            [
                "CT0001_A1_001",
                "CT0001",
                multiline_name,
                "Blood Disorders",
                "Subcutaneous",
                "10.0",
                "1.0",
                "10.0",
            ],
            [
                "CT0002_A1_001",
                "CT0002",
                "infliximab",
                "Blood Disorders",
                "Intravenous",
                "20.0",
                "2.0",
                "10.0",
            ],
        ],
    )

    cohorts = load_cohorts(path)

    assert len(cohorts) == 2
    assert cohorts[0].inn_name == multiline_name
    assert cohorts[0].n_analyzed == 10
    assert cohorts[1].row_id == "CT0002_A1_001"
    assert cohorts[1].inn_name == "infliximab"
    assert cohorts[1].n_analyzed == 20


def test_ac2_cohort_has_the_expected_fields(cohorts_csv: Path) -> None:
    """AC2: field names, types and one exact sample record."""
    cohorts = load_cohorts(cohorts_csv)
    first = cohorts[0]

    assert isinstance(first, Cohort)
    assert first.row_id == "CT0046_A1_001"
    assert first.trial_id == "CT0046"
    assert first.inn_name == "Nonacog alfa"
    assert first.indication_category == "Blood Disorders"
    assert first.route == "Intravenous"
    assert first.n_analyzed == 25
    assert first.n_ada_positive == 1
    assert first.ada_frequency_percent == pytest.approx(4.0)


def test_ac2_numeric_fields_are_int_or_float_or_missing(cohorts_csv: Path) -> None:
    """AC2: counts are integers or missing, the frequency is a decimal or missing."""
    for cohort in load_cohorts(cohorts_csv):
        assert cohort.n_analyzed is None or isinstance(cohort.n_analyzed, int)
        assert cohort.n_ada_positive is None or isinstance(cohort.n_ada_positive, int)
        assert cohort.ada_frequency_percent is None or isinstance(
            cohort.ada_frequency_percent, float
        )


def test_ac2_frequency_is_a_percentage(cohorts_csv: Path) -> None:
    """AC2: the frequency is given in percent, so it lies between 0 and 100."""
    frequencies = [c.ada_frequency_percent for c in load_cohorts(cohorts_csv)]
    assert all(value is not None and 0.0 <= value <= 100.0 for value in frequencies)
    assert max(frequencies) == pytest.approx(100.0)


def test_ac3_empty_ada_positive_count_stays_missing(tmp_path: Path) -> None:
    """AC3: an empty `Number of ADA+ patients` is missing, not 0."""
    path = write_csv(
        tmp_path / "clinical_trials.csv",
        REQUIRED_COLUMNS,
        [
            [
                "CT0001_A1_001",
                "CT0001",
                "adalimumab",
                "Blood Disorders",
                "Subcutaneous",
                "10.0",
                "",
                "",
            ]
        ],
    )

    cohort = load_cohorts(path)[0]

    assert cohort.n_ada_positive is None
    assert cohort.n_analyzed == 10
    # A blank ADA rate is missing too, never filled with 0.0.
    assert cohort.ada_frequency_percent is None


@pytest.mark.parametrize("missing_column", REQUIRED_COLUMNS)
def test_ac4_missing_required_column_is_named_in_the_error(
    tmp_path: Path, missing_column: str
) -> None:
    """AC4: a missing required column raises an error that names the column."""
    columns = [column for column in REQUIRED_COLUMNS if column != missing_column]
    path = write_csv(tmp_path / "clinical_trials.csv", columns, [])

    with pytest.raises(ValueError, match=re.escape(missing_column)):
        load_cohorts(path)
