"""Tests for the data layer (spec 001, AC1 to AC8b)."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import get_type_hints

import pytest

from ida.data import (
    PAGE_SIZE,
    DataFormatError,
    filter_cohorts,
    load_cohorts,
    paginate,
)
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


# --- AC2 (as amended) and AC4b: number rules -------------------------------


def test_ac2_amended_ada_positive_is_int_or_missing_in_the_fixture(
    cohorts_csv: Path,
) -> None:
    """AC2 as amended: `n_ada_positive` is an int, a non-whole decimal, or missing."""
    # The annotation itself is the amended AC2 contract: reverting it to
    # `int | None` must fail here even though the fixture only holds whole counts.
    assert get_type_hints(Cohort)["n_ada_positive"] == int | float | None

    for cohort in load_cohorts(cohorts_csv):
        assert cohort.n_ada_positive is None or isinstance(cohort.n_ada_positive, int | float)
        # The fixture has no non-whole ADA+ count, so every value is an int.
        assert cohort.n_ada_positive is None or isinstance(cohort.n_ada_positive, int)


def test_ac4b_whole_and_non_whole_ada_positive_counts_are_kept(tmp_path: Path) -> None:
    """AC4b: `25.0` loads as the int 25, `62.7` as the float 62.7, nothing rounded."""
    path = write_csv(
        tmp_path / "clinical_trials.csv",
        REQUIRED_COLUMNS,
        [
            [
                "CT0670_A1_001",
                "CT0670",
                "adalimumab",
                "Blood Disorders",
                "Subcutaneous",
                "100",
                "25.0",
                "25.0",
            ],
            [
                "CT0710_A1_002",
                "CT0710",
                "adalimumab",
                "Blood Disorders",
                "Subcutaneous",
                "1000",
                "62.7",
                "6.27",
            ],
        ],
    )

    whole, non_whole = load_cohorts(path)

    assert whole.n_ada_positive == 25
    assert isinstance(whole.n_ada_positive, int)
    assert non_whole.n_ada_positive == pytest.approx(62.7)
    assert isinstance(non_whole.n_ada_positive, float)


# --- AC4c: malformed numbers ----------------------------------------------

MALFORMED_CASES = [
    ("2.5", "10.0", "4.0", "Number of Patients analyzed for ADA"),
    ("10.0", "abc", "4.0", "Number of ADA+ patients"),
    ("10.0", "-1", "4.0", "Number of ADA+ patients"),
    ("10.0", "1.0", "nan", "Frequency of ADA+ patients"),
    ("10.0", "1.0", "inf", "Frequency of ADA+ patients"),
    ("10.0", "1.0", "101", "Frequency of ADA+ patients"),
]


@pytest.mark.parametrize(
    ("n_analyzed", "n_ada_positive", "frequency", "column"),
    MALFORMED_CASES,
    ids=["analyzed-2.5", "ada-abc", "ada-negative", "freq-nan", "freq-inf", "freq-101"],
)
def test_ac4c_malformed_number_raises_data_format_error(
    tmp_path: Path,
    n_analyzed: str,
    n_ada_positive: str,
    frequency: str,
    column: str,
) -> None:
    """AC4c: one file per malformed case raises `DataFormatError` naming row and column."""
    row_id = "CT9999_A1_001"
    path = write_csv(
        tmp_path / "clinical_trials.csv",
        REQUIRED_COLUMNS,
        [
            [
                row_id,
                "CT9999",
                "adalimumab",
                "Blood Disorders",
                "Subcutaneous",
                n_analyzed,
                n_ada_positive,
                frequency,
            ]
        ],
    )

    with pytest.raises(DataFormatError) as excinfo:
        load_cohorts(path)

    message = str(excinfo.value)
    assert row_id in message
    assert column in message
    # `DataFormatError` is a `ValueError`, as the contract requires.
    assert isinstance(excinfo.value, ValueError)


def test_ac4d_unmeasured_row_is_skipped_before_validation(tmp_path: Path) -> None:
    """AC4d: a row without `Number of Patients analyzed for ADA` is never validated."""
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
                "",
                "abc",
                "4.0",
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

    assert [cohort.row_id for cohort in cohorts] == ["CT0002_A1_001"]


# --- Data access contract: logging-safe messages and exact decimals --------

SYNTHETIC_CELL_MARKER = "SYNTHETIC_CELL_MARKER"


@pytest.mark.parametrize(
    ("n_analyzed", "n_ada_positive", "frequency", "column"),
    [
        (SYNTHETIC_CELL_MARKER, "1.0", "4.0", "Number of Patients analyzed for ADA"),
        ("10.0", SYNTHETIC_CELL_MARKER, "4.0", "Number of ADA+ patients"),
        ("10.0", "1.0", SYNTHETIC_CELL_MARKER, "Frequency of ADA+ patients"),
    ],
    ids=["analyzed", "ada-positive", "frequency"],
)
def test_data_format_error_message_never_contains_the_raw_cell(
    tmp_path: Path,
    n_analyzed: str,
    n_ada_positive: str,
    frequency: str,
    column: str,
) -> None:
    """Data access contract: the message names row and column, never the cell.

    The message may be logged, so it must not leak row data.
    """
    row_id = "TEST_ROW"
    path = write_csv(
        tmp_path / "clinical_trials.csv",
        REQUIRED_COLUMNS,
        [
            [
                row_id,
                "CT0001",
                "adalimumab",
                "Blood Disorders",
                "Subcutaneous",
                n_analyzed,
                n_ada_positive,
                frequency,
            ]
        ],
    )

    with pytest.raises(DataFormatError) as excinfo:
        load_cohorts(path)

    message = str(excinfo.value)
    assert SYNTHETIC_CELL_MARKER not in message
    assert row_id in message
    assert column in message


def test_analyzed_count_is_validated_on_the_exact_source_decimal(tmp_path: Path) -> None:
    """A value just above a whole number is malformed, not rounded down to it."""
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
                "2.0000000000000001",
                "1",
                "4.0",
            ]
        ],
    )

    with pytest.raises(DataFormatError) as excinfo:
        load_cohorts(path)

    message = str(excinfo.value)
    assert "CT0001_A1_001" in message
    assert "Number of Patients analyzed for ADA" in message


def test_large_whole_analyzed_count_keeps_its_exact_value(tmp_path: Path) -> None:
    """A whole count beyond float precision loads as the exact `int`, not rounded."""
    exact = 9007199254740993  # 2**53 + 1, not representable as a float
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
                str(exact),
                "1",
                "4.0",
            ]
        ],
    )

    cohort = load_cohorts(path)[0]

    assert cohort.n_analyzed == exact
    assert isinstance(cohort.n_analyzed, int)


def test_large_whole_ada_positive_count_keeps_its_exact_value(tmp_path: Path) -> None:
    """A whole ADA+ count beyond float precision loads as the exact `int`."""
    exact = 9007199254740993  # 2**53 + 1, not representable as a float
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
                str(exact),
                str(exact),
                "4.0",
            ]
        ],
    )

    cohort = load_cohorts(path)[0]

    assert cohort.n_ada_positive == exact
    assert isinstance(cohort.n_ada_positive, int)


def test_frequency_just_above_100_is_rejected(tmp_path: Path) -> None:
    """A rate above 100 is malformed even if it would round to 100.0 as a float."""
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
                "10",
                "1",
                "100.0000000000000001",
            ]
        ],
    )

    with pytest.raises(DataFormatError) as excinfo:
        load_cohorts(path)

    message = str(excinfo.value)
    assert "CT0001_A1_001" in message
    assert "Frequency of ADA+ patients" in message


def test_frequency_of_exactly_100_is_accepted(tmp_path: Path) -> None:
    """The upper bound is inclusive; a rate of exactly 100 loads as a `float`."""
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
                "10",
                "1",
                "100",
            ]
        ],
    )

    cohort = load_cohorts(path)[0]

    assert cohort.ada_frequency_percent == pytest.approx(100.0)
    assert isinstance(cohort.ada_frequency_percent, float)


# --- AC5 to AC8: filters ---------------------------------------------------


def test_ac5_inn_filter_is_a_case_insensitive_substring(cohorts_csv: Path) -> None:
    """AC5: `inn="adalimumab"` yields the 4 Adalimumab cohorts."""
    cohorts = load_cohorts(cohorts_csv)

    result = filter_cohorts(cohorts, inn="adalimumab")

    assert len(result) == 4
    assert all("adalimumab" in cohort.inn_name.lower() for cohort in result)


def test_ac5_inn_filter_matches_a_substring_not_only_the_full_name(
    cohorts_csv: Path,
) -> None:
    """AC5 (Filter rules): `inn` matches a substring, so `adalim` finds the same 4."""
    cohorts = load_cohorts(cohorts_csv)

    result = filter_cohorts(cohorts, inn="adalim")

    assert len(result) == 4
    assert all(
        cohort.inn_name is not None and "adalim" in cohort.inn_name.lower() for cohort in result
    )


def test_exact_filters_do_not_match_a_different_case(cohorts_csv: Path) -> None:
    """Filter rules: `indication` and `route` are exact and case-sensitive."""
    cohorts = load_cohorts(cohorts_csv)

    assert filter_cohorts(cohorts, indication="cancer and neoplasms") == []
    assert filter_cohorts(cohorts, route="subcutaneous") == []


def test_ac6_indication_filter_is_exact_and_case_sensitive(cohorts_csv: Path) -> None:
    """AC6: `indication="Cancer and neoplasms"` yields exactly 2 cohorts."""
    cohorts = load_cohorts(cohorts_csv)

    result = filter_cohorts(cohorts, indication="Cancer and neoplasms")

    assert len(result) == 2
    assert all(cohort.indication_category == "Cancer and neoplasms" for cohort in result)


def test_ac7_filters_are_combined_with_and(cohorts_csv: Path) -> None:
    """AC7: `inn` plus `route` narrow to the 4 Subcutaneous Adalimumab cohorts."""
    cohorts = load_cohorts(cohorts_csv)

    subcutaneous = filter_cohorts(cohorts, inn="adalimumab", route="Subcutaneous")
    intravenous = filter_cohorts(cohorts, inn="adalimumab", route="Intravenous")

    assert len(subcutaneous) == 4
    assert all(
        "adalimumab" in cohort.inn_name.lower() and cohort.route == "Subcutaneous"
        for cohort in subcutaneous
    )
    assert intravenous == []


@pytest.mark.parametrize(
    "filters",
    [
        {},
        {"inn": ""},
        {"inn": "", "indication": "", "route": ""},
        {"inn": "   ", "indication": "\t", "route": " \n "},
    ],
    ids=["no-filter", "one-empty", "all-empty", "all-whitespace"],
)
def test_ac8_no_effective_filter_returns_all_cohorts_in_file_order(
    cohorts_csv: Path, filters: dict[str, str]
) -> None:
    """AC8: no filter, or empty/whitespace filters, return all 30 in file order."""
    cohorts = load_cohorts(cohorts_csv)

    result = filter_cohorts(cohorts, **filters)

    assert len(result) == 30
    assert [cohort.row_id for cohort in result] == [cohort.row_id for cohort in cohorts]


def test_filter_never_matches_a_missing_field() -> None:
    """Filter rules: a cohort with a missing field never matches an active filter."""
    missing_inn = Cohort(
        row_id="CT0001_A1_001",
        trial_id="CT0001",
        inn_name=None,
        indication_category=None,
        route=None,
        n_analyzed=10,
        n_ada_positive=1,
        ada_frequency_percent=10.0,
    )

    assert filter_cohorts([missing_inn], inn="ada") == []
    assert filter_cohorts([missing_inn], indication="Blood Disorders") == []
    assert filter_cohorts([missing_inn], route="Subcutaneous") == []


# --- AC8b: pagination ------------------------------------------------------


def synthetic_cohorts(count: int) -> list[Cohort]:
    """Build `count` distinguishable synthetic cohorts for pagination tests."""
    return [
        Cohort(
            row_id=f"CT{index:04d}_A1_001",
            trial_id=f"CT{index:04d}",
            inn_name="adalimumab",
            indication_category="Blood Disorders",
            route="Subcutaneous",
            n_analyzed=100,
            n_ada_positive=1,
            ada_frequency_percent=1.0,
        )
        for index in range(1, count + 1)
    ]


def test_ac8b_paginate_splits_120_items_into_pages_of_50() -> None:
    """AC8b: pages 1 to 4 hold 50, 50, 20 and 0 items with a real total of 120."""
    cohorts = synthetic_cohorts(120)

    pages = [paginate(cohorts, page) for page in (1, 2, 3, 4)]

    assert PAGE_SIZE == 50
    assert [len(page.items) for page in pages] == [50, 50, 20, 0]
    assert all(page.total == 120 for page in pages)
    assert all(page.page_size == 50 for page in pages)
    assert [page.page for page in pages] == [1, 2, 3, 4]
    assert pages[0].items[0] is cohorts[0]
    assert pages[1].items[0] is cohorts[50]
    assert pages[2].items[-1] is cohorts[119]


def test_ac8b_paginate_rejects_a_page_below_one() -> None:
    """AC8b: `paginate(items, 0)` raises `ValueError`."""
    with pytest.raises(ValueError):
        paginate(synthetic_cohorts(120), 0)


def test_ac8b_page_is_a_frozen_dataclass_with_the_contract_fields() -> None:
    """Page exposes `total`, `page`, `page_size` and `items` and is immutable."""
    page = paginate(synthetic_cohorts(3), 1)

    assert (page.total, page.page, page.page_size) == (3, 1, 50)
    with pytest.raises(AttributeError):
        page.total = 4  # type: ignore[misc]


def test_ac8b_empty_input_has_zero_total_and_no_items() -> None:
    """An empty list paginates to a page with `total` 0 and an empty `items`."""
    page = paginate([], 1)

    assert page.total == 0
    assert page.items == []
