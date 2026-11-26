"""Loading and filtering cohorts from the IDC dataset.

The CSV file contains line breaks inside fields, so it is read with pandas'
CSV parser, never line by line. Column names are used exactly as in the dataset.
"""

from __future__ import annotations

import decimal
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

import pandas as pd

from ida.models import Cohort

#: Plain decimal number syntax accepted from the source CSV. Underscores, spaces
#: and other syntax that `Decimal` would interpret loosely are rejected.
_NUMBER_SYNTAX = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")

#: Number of items on one page of the table and the JSON interface.
PAGE_SIZE = 50

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


class DataFormatError(ValueError):
    """Raised when a measured row holds a value that does not follow the number rules.

    The message names the row identifier and the column, nothing else. It never
    contains the offending cell, so it is safe to log (see the data access
    contract in the spec).
    """

    def __init__(self, row_id: str | None, column: str) -> None:
        self.row_id = row_id
        self.column = column
        super().__init__(f"Invalid value in column {column!r} for row {row_id!r}")


def _to_decimal(value: object, *, row_id: str | None, column: str) -> decimal.Decimal | None:
    """Parse a finite decimal from the source text without rounding, or raise.

    Validation happens on the exact source decimal; only validated values are
    converted to `int` or `float` afterwards. The source text must match a strict
    plain-number syntax: `Decimal` accepts underscores as digit separators (it
    follows Python's numeric literal rules), which would silently turn `1__0`
    into `10`; those cells are rejected instead.
    """
    text = _text(value)
    if text is None:
        return None
    if not _NUMBER_SYNTAX.fullmatch(text):
        raise DataFormatError(row_id, column)
    try:
        number = decimal.Decimal(text)
    except (decimal.InvalidOperation, ValueError) as error:
        raise DataFormatError(row_id, column) from error
    if not number.is_finite():
        raise DataFormatError(row_id, column)
    return number


def _to_whole(value: object, *, row_id: str | None, column: str) -> int | None:
    """Parse a whole number >= 0; `25` and `25.0` both load as the exact `int` 25."""
    number = _to_decimal(value, row_id=row_id, column=column)
    if number is None:
        return None
    if number < 0 or number != number.to_integral_value():
        raise DataFormatError(row_id, column)
    return int(number)


def _to_count(value: object, *, row_id: str | None, column: str) -> int | float | None:
    """Parse a count >= 0; a whole value loads as exact `int`, a non-whole one as `float`."""
    number = _to_decimal(value, row_id=row_id, column=column)
    if number is None:
        return None
    if number < 0:
        raise DataFormatError(row_id, column)
    if number == number.to_integral_value():
        return int(number)
    result = float(number)
    if not math.isfinite(result) or (number > 0 and result == 0.0):
        raise DataFormatError(row_id, column)
    return result


def _to_frequency(value: object, *, row_id: str | None, column: str) -> float | None:
    """Parse an ADA rate in percent: a finite number between 0 and 100 inclusive."""
    number = _to_decimal(value, row_id=row_id, column=column)
    if number is None:
        return None
    if not decimal.Decimal(0) <= number <= decimal.Decimal(100):
        raise DataFormatError(row_id, column)
    result = float(number)
    if number > 0 and result == 0.0:
        raise DataFormatError(row_id, column)
    return result


def load_cohorts(path: str | Path) -> list[Cohort]:
    """Load the cohorts with a measured ADA value from a `clinical_trials.csv` file.

    Rows without a value in `Number of Patients analyzed for ADA` are not a
    cohort with a measured value and are dropped before any validation.
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

    cohorts: list[Cohort] = []
    for _, row in measured.iterrows():
        row_id = _text(row[COL_ROW_ID])
        cohorts.append(
            Cohort(
                row_id=row_id,
                trial_id=_text(row[COL_TRIAL_ID]),
                inn_name=_text(row[COL_INN_NAME]),
                indication_category=_text(row[COL_INDICATION]),
                route=_text(row[COL_ROUTE]),
                n_analyzed=_to_whole(row[COL_N_ANALYZED], row_id=row_id, column=COL_N_ANALYZED),
                n_ada_positive=_to_count(
                    row[COL_N_ADA_POSITIVE], row_id=row_id, column=COL_N_ADA_POSITIVE
                ),
                ada_frequency_percent=_to_frequency(
                    row[COL_FREQUENCY], row_id=row_id, column=COL_FREQUENCY
                ),
            )
        )
    return cohorts


def _normalized(value: str | None) -> str | None:
    """Strip a filter parameter; an empty result means "no filter"."""
    if value is None:
        return None
    text = value.strip()
    return text or None


def filter_cohorts(
    cohorts: list[Cohort],
    inn: str | None = None,
    indication: str | None = None,
    route: str | None = None,
) -> list[Cohort]:
    """Filter cohorts, keeping the input order and combining all filters with AND.

    `inn` matches as a case-insensitive substring, `indication` and `route`
    match exactly and case-sensitively. A cohort whose field is missing never
    matches an active filter on that field.
    """
    inn_needle = _normalized(inn)
    inn_needle = inn_needle.lower() if inn_needle is not None else None
    indication_value = _normalized(indication)
    route_value = _normalized(route)

    def matches(cohort: Cohort) -> bool:
        if inn_needle is not None and (
            cohort.inn_name is None or inn_needle not in cohort.inn_name.lower()
        ):
            return False
        if indication_value is not None and cohort.indication_category != indication_value:
            return False
        return route_value is None or cohort.route == route_value

    return [cohort for cohort in cohorts if matches(cohort)]


T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    """One page of items plus the total number of items before pagination."""

    total: int
    page: int
    page_size: int
    items: list[T]


def paginate(items: list[T], page: int) -> Page[T]:
    """Return the 1-based `page` of `items`, `PAGE_SIZE` items per page.

    A page beyond the last one holds an empty `items` list and the real `total`.
    """
    if page < 1:
        raise ValueError(f"page must be >= 1, got {page}")
    start = (page - 1) * PAGE_SIZE
    return Page(
        total=len(items),
        page=page,
        page_size=PAGE_SIZE,
        items=list(items[start : start + PAGE_SIZE]),
    )
