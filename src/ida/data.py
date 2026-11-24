"""Loading cohorts from the IDC dataset.

The CSV file contains line breaks inside fields, so it is read with pandas'
CSV parser, never line by line. Column names are used exactly as in the dataset.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ida.models import Cohort

COL_ROW_ID = "IDC Row identifier"
COL_TRIAL_ID = "Trial ID"
COL_INN_NAME = "Molecule Assessed for ADA INN Name"
COL_INDICATION = "Disease Indication Category"
COL_ROUTE = "Therapeutic Route of Administration"
COL_N_ANALYZED = "Number of Patients analyzed for ADA"
COL_N_ADA_POSITIVE = "Number of ADA+ patients"
COL_FREQUENCY = "Frequency of ADA+ patients"

#: Columns the application reads. A file without one of them is not usable.
REQUIRED_COLUMNS = (
    COL_ROW_ID,
    COL_TRIAL_ID,
    COL_INN_NAME,
    COL_INDICATION,
    COL_ROUTE,
    COL_N_ANALYZED,
    COL_N_ADA_POSITIVE,
    COL_FREQUENCY,
)


class MissingColumnError(ValueError):
    """Raised when the CSV file lacks a required column."""

    def __init__(self, column: str) -> None:
        self.column = column
        super().__init__(f"Missing required column: {column!r}")


def _text(value: object) -> str | None:
    """Return a stripped string, or `None` for a missing value."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _to_int(value: object) -> int | None:
    text = _text(value)
    if text is None:
        return None
    return int(float(text))


def _to_float(value: object) -> float | None:
    text = _text(value)
    if text is None:
        return None
    return float(text)


def load_cohorts(path: str | Path) -> list[Cohort]:
    """Load the cohorts with a measured ADA value from a `clinical_trials.csv` file.

    Rows without a value in `Number of Patients analyzed for ADA` are not a
    cohort with a measured value and are dropped.
    """
    frame = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_values=[],
        encoding="utf-8",
    )

    for column in REQUIRED_COLUMNS:
        if column not in frame.columns:
            raise MissingColumnError(column)

    measured = frame[frame[COL_N_ANALYZED].str.strip() != ""]

    return [
        Cohort(
            row_id=_text(row[COL_ROW_ID]),
            trial_id=_text(row[COL_TRIAL_ID]),
            inn_name=_text(row[COL_INN_NAME]),
            indication_category=_text(row[COL_INDICATION]),
            route=_text(row[COL_ROUTE]),
            n_analyzed=_to_int(row[COL_N_ANALYZED]),
            n_ada_positive=_to_int(row[COL_N_ADA_POSITIVE]),
            ada_frequency_percent=_to_float(row[COL_FREQUENCY]),
        )
        for _, row in measured.iterrows()
    ]
