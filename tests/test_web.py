"""Tests for the web interface (spec 001, AC9 to AC16b, AC22, AC22b).

The filter form and the page parameter belong to slice 4, the JSON interface to
slice 5; this module covers the first rendered page of `GET /` and the
unavailable-data handling.
"""

from __future__ import annotations

import csv
import logging
import re
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ida.app import app, get_cohorts, reset_cohorts_cache
from ida.data import load_cohorts
from ida.models import Cohort

#: The context notice exactly as written in the page contract.
CONTEXT_NOTICE = (
    "ADA rates of different therapeutics are not comparable without their clinical context. "
    "This page serves research only and makes no medical or regulatory statement."
)

#: Footer facts required on every HTML page.
FOOTER_TEXTS = (
    "Immunogenicity Database Collaborative",
    "CC BY 4.0",
    "10.3389/fimmu.2026.1816949",
)

#: The columns `load_cohorts` requires, written exactly as in the dataset.
DATA_HEADER = (
    "IDC Row identifier",
    "Trial ID",
    "Molecule Assessed for ADA INN Name",
    "Disease Indication Category",
    "Therapeutic Route of Administration",
    "Number of Patients analyzed for ADA",
    "Number of ADA+ patients",
    "Frequency of ADA+ patients",
)

client = TestClient(app)


@pytest.fixture
def use_cohorts() -> Iterator[Callable[[list[Cohort]], TestClient]]:
    """Replace the `get_cohorts` dependency with the given cohorts."""

    def _use(cohorts: list[Cohort]) -> TestClient:
        app.dependency_overrides[get_cohorts] = lambda: cohorts
        return client

    yield _use
    app.dependency_overrides.pop(get_cohorts, None)


def without_comments(html: str) -> str:
    """Return the page with HTML comments removed, so hidden markup never counts."""
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def element_text(html: str, element_id: str, tag: str = "p") -> str:
    """Return the stripped text of the visible element with the given id."""
    match = re.search(rf'<{tag} id="{element_id}">(.*?)</{tag}>', without_comments(html), re.S)
    assert match is not None, f"the page has no {tag} element with id {element_id!r}"
    return match.group(1).strip()


def table_body_rows(html: str) -> list[str]:
    """Return the inner HTML of every `<tr>` of the `table#cohorts` body."""
    table = re.search(r'<table id="cohorts">(.*?)</table>', without_comments(html), re.S)
    assert table is not None, "the page has no table with id 'cohorts'"
    bodies = re.findall(r"<tbody>(.*?)</tbody>", table.group(1), re.S)
    assert len(bodies) == 1, "the cohort table must have exactly one body"
    return re.findall(r"<tr>(.*?)</tr>", bodies[0], re.S)


def row_cells(row: str) -> list[str]:
    """Return the stripped text of every `<td>` of one table row."""
    return [cell.strip() for cell in re.findall(r"<td>(.*?)</td>", row, re.S)]


def text_of(html: str, element_id: str) -> str:
    """Return the stripped text of the `<p>` with the given id."""
    return element_text(html, element_id)


def footer_text(html: str) -> str:
    """Return the inner text of the visible page footer."""
    return element_text(html, "footer", "footer")


def context_notice_text(html: str) -> str:
    """Return the inner text of the context notice."""
    return element_text(html, "context-notice")


def synthetic_cohorts(make_cohort: Callable[..., Cohort], count: int) -> list[Cohort]:
    """Return `count` distinct synthetic cohorts in file order."""
    return [
        make_cohort(row_id=f"CT{index:04d}_A1_001", trial_id=f"CT{index:04d}")
        for index in range(count)
    ]


def test_ac9_renders_the_thirty_fixture_cohorts(
    use_cohorts: Callable[[list[Cohort]], TestClient], cohorts_csv: Path
) -> None:
    """AC9: 200, HTML, 30 body rows and `30 results`."""
    response = use_cohorts(load_cohorts(cohorts_csv)).get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert len(table_body_rows(response.text)) == 30
    assert text_of(response.text, "total") == "30 results"


def test_ac10_first_page_holds_fifty_of_120_cohorts(
    use_cohorts: Callable[[list[Cohort]], TestClient], make_cohort: Callable[..., Cohort]
) -> None:
    """AC10: the first page shows PAGE_SIZE rows but the real total."""
    cohorts = synthetic_cohorts(make_cohort, 120)
    response = use_cohorts(cohorts).get("/")

    rows = table_body_rows(response.text)
    assert len(rows) == 50
    assert text_of(response.text, "total") == "120 results"
    # The rows are the first page in file order.
    assert row_cells(rows[0])[0] == "CT0000"
    assert row_cells(rows[-1])[0] == "CT0049"


def test_empty_table_renders_the_empty_notice(
    use_cohorts: Callable[[list[Cohort]], TestClient],
) -> None:
    """An empty data set renders the table with no rows and the empty notice."""
    html = use_cohorts([]).get("/").text

    assert table_body_rows(html) == []
    assert text_of(html, "total") == "0 results"
    assert text_of(html, "empty") == "No results"


def test_ac15_page_carries_footer_and_license(
    use_cohorts: Callable[[list[Cohort]], TestClient], cohorts_csv: Path
) -> None:
    """AC15: source attribution, license and DOI are on the page."""
    footer = footer_text(use_cohorts(load_cohorts(cohorts_csv)).get("/").text)

    for text in FOOTER_TEXTS:
        assert text in footer


def test_ac15b_page_carries_context_notice(
    use_cohorts: Callable[[list[Cohort]], TestClient], cohorts_csv: Path
) -> None:
    """AC15b: the context notice is on the page exactly as specified."""
    html = use_cohorts(load_cohorts(cohorts_csv)).get("/").text

    assert context_notice_text(html) == CONTEXT_NOTICE


def test_ac16_missing_values_render_as_dash(
    use_cohorts: Callable[[list[Cohort]], TestClient], make_cohort: Callable[..., Cohort]
) -> None:
    """AC16: missing ADA+ count and rate show the en dash, never a number."""
    cohort = make_cohort(n_ada_positive=None, ada_frequency_percent=None)
    html = use_cohorts([cohort]).get("/").text

    cells = row_cells(table_body_rows(html)[0])
    assert cells[5] == "\u2013"
    assert cells[6] == "\u2013"
    for cell in cells[5:]:
        assert cell not in {"0", "None", "nan"}


def test_ac16b_numbers_use_the_specified_format(
    use_cohorts: Callable[[list[Cohort]], TestClient], make_cohort: Callable[..., Cohort]
) -> None:
    """AC16b: 62.7 stays `62.7`, the rate `4.0`, a whole count `25`."""
    cohorts = [
        make_cohort(row_id="CT0001_A1_001", n_ada_positive=62.7, ada_frequency_percent=4.0),
        make_cohort(row_id="CT0002_A1_001", n_ada_positive=25, ada_frequency_percent=2.36),
    ]
    html = use_cohorts(cohorts).get("/").text

    first, second = (row_cells(row) for row in table_body_rows(html))
    assert first[5] == "62.7"
    assert first[6] == "4.0"
    assert second[5] == "25"
    assert second[6] == "2.4"


def test_ac22_unavailable_data_answers_503_page_and_health_stays_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC22 (HTML and /health): 503 page with footer and notice; /health is 200."""
    data_dir = tmp_path / "idc"
    data_dir.mkdir()
    monkeypatch.setenv("IDA_DATA_DIR", str(data_dir))
    reset_cohorts_cache()

    response = client.get("/")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("text/html")
    assert "Data not available" in response.text
    footer = footer_text(response.text)
    for text in FOOTER_TEXTS:
        assert text in footer
    assert context_notice_text(response.text) == CONTEXT_NOTICE

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


def test_ac22b_failed_load_is_not_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cohorts_csv: Path
) -> None:
    """AC22b: after providing the file, the next request succeeds without a reset."""
    data_dir = tmp_path / "idc"
    monkeypatch.setenv("IDA_DATA_DIR", str(data_dir))
    reset_cohorts_cache()

    first = client.get("/")
    assert first.status_code == 503

    data_dir.mkdir()
    shutil.copyfile(cohorts_csv, data_dir / "clinical_trials.csv")

    second = client.get("/")
    assert second.status_code == 200
    assert text_of(second.text, "total") == "30 results"


def test_ac22b_successful_load_is_cached_until_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cohorts_csv: Path
) -> None:
    """AC22b: a successful load survives the file disappearing; reset empties it."""
    data_dir = tmp_path / "idc"
    data_dir.mkdir()
    csv_path = data_dir / "clinical_trials.csv"
    shutil.copyfile(cohorts_csv, csv_path)
    monkeypatch.setenv("IDA_DATA_DIR", str(data_dir))
    reset_cohorts_cache()

    first = client.get("/")
    assert first.status_code == 200
    assert text_of(first.text, "total") == "30 results"

    csv_path.unlink()
    cached = client.get("/")
    assert cached.status_code == 200
    assert text_of(cached.text, "total") == "30 results"

    reset_cohorts_cache()
    after_reset = client.get("/")
    assert after_reset.status_code == 503


def test_health_never_invokes_the_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    """`/health` is a liveness signal and never calls `get_cohorts`."""
    calls: list[tuple[object, ...]] = []

    def spy(*args: object, **kwargs: object) -> None:
        calls.append(args)
        raise AssertionError("/health must not load cohort data")

    monkeypatch.setattr("ida.app.load_cohorts", spy)
    reset_cohorts_cache()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert calls == []


def test_failed_load_logs_the_exception_type_without_its_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A missing file is logged with its type; the message (with the path) is not."""
    data_dir = tmp_path / "missing"
    monkeypatch.setenv("IDA_DATA_DIR", str(data_dir))
    reset_cohorts_cache()

    with caplog.at_level(logging.ERROR):
        response = client.get("/")

    assert response.status_code == 503
    messages = [record.getMessage() for record in caplog.records]
    assert any("FileNotFoundError" in message for message in messages)
    assert all(str(data_dir) not in message for message in messages)


def test_missing_column_error_message_is_logged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A `MissingColumnError` logs its message, which holds only the column name."""
    data_dir = tmp_path / "idc"
    data_dir.mkdir()
    with (data_dir / "clinical_trials.csv").open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerow(["IDC Row identifier", "Trial ID"])
    monkeypatch.setenv("IDA_DATA_DIR", str(data_dir))
    reset_cohorts_cache()

    with caplog.at_level(logging.ERROR):
        response = client.get("/")

    assert response.status_code == 503
    messages = [record.getMessage() for record in caplog.records]
    assert any("MissingColumnError" in message for message in messages)
    assert any("Missing required column" in message for message in messages)


def test_data_format_error_answers_503_and_logs_without_the_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """AC22: a malformed value is a 503; the log names row and column, not the cell."""
    data_dir = tmp_path / "idc"
    data_dir.mkdir()
    with (data_dir / "clinical_trials.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(DATA_HEADER)
        writer.writerow(
            [
                "CT9999_A1_001",
                "CT9999",
                "Testmab",
                "Healthy volunteers",
                "Subcutaneous",
                "100",
                "abc",
                "5.0",
            ]
        )
    monkeypatch.setenv("IDA_DATA_DIR", str(data_dir))
    reset_cohorts_cache()

    with caplog.at_level(logging.ERROR):
        response = client.get("/")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("text/html")
    assert "Data not available" in response.text
    messages = [record.getMessage() for record in caplog.records]
    assert any("DataFormatError" in message for message in messages)
    assert any("Number of ADA+ patients" in message for message in messages)
    assert any("CT9999_A1_001" in message for message in messages)
    # The malformed cell itself must never reach the log.
    assert all("abc" not in message for message in messages)
