"""Tests for the JSON interface (spec 001, AC17 to AC19 and AC25, JSON part of AC22).

The endpoint `GET /api/cohorts` serves the same filtered, paginated cohorts as
the web interface, but with the numbers as loaded (no rounding) and `null` for
missing values. Tests never read `data/idc/`: the dependency is replaced with
fixture or synthetic cohorts.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import asdict
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ida.app import app, get_cohorts, reset_cohorts_cache
from ida.data import load_cohorts
from ida.models import Cohort

#: The field names from AC2, in the order of the `Cohort` dataclass.
COHORT_FIELDS = {
    "row_id",
    "trial_id",
    "inn_name",
    "indication_category",
    "route",
    "n_analyzed",
    "n_ada_positive",
    "ada_frequency_percent",
}

client = TestClient(app)


@pytest.fixture
def use_cohorts() -> Iterator[Callable[[list[Cohort]], TestClient]]:
    """Replace the `get_cohorts` dependency with the given cohorts."""

    def _use(cohorts: list[Cohort]) -> TestClient:
        app.dependency_overrides[get_cohorts] = lambda: cohorts
        return client

    yield _use
    app.dependency_overrides.pop(get_cohorts, None)


def synthetic_cohorts(
    make_cohort: Callable[..., Cohort], count: int, **overrides: object
) -> list[Cohort]:
    """Return `count` distinct synthetic cohorts in file order."""
    return [
        make_cohort(row_id=f"CT{index:04d}_A1_001", trial_id=f"CT{index:04d}", **overrides)
        for index in range(count)
    ]


def test_ac17_serves_all_fixture_cohorts_with_the_contract_keys(
    use_cohorts: Callable[[list[Cohort]], TestClient], cohorts_csv: Path
) -> None:
    """AC17: 200, the four response keys and 30 items with exactly the AC2 fields."""
    cohorts = load_cohorts(cohorts_csv)
    response = use_cohorts(cohorts).get("/api/cohorts")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert set(payload) == {"total", "page", "page_size", "items"}
    assert payload["total"] == 30
    assert payload["page"] == 1
    assert payload["page_size"] == 50

    items = payload["items"]
    assert len(items) == 30
    for item in items:
        assert set(item) == COHORT_FIELDS
    # File order and values as loaded, not re-formatted.
    assert items == [asdict(cohort) for cohort in cohorts]


def test_ac18_inn_filter_narrows_the_json_items(
    use_cohorts: Callable[[list[Cohort]], TestClient], cohorts_csv: Path
) -> None:
    """AC18: `inn=adalimumab` gives total 4 and the 4 Adalimumab items."""
    cohorts = load_cohorts(cohorts_csv)
    payload = use_cohorts(cohorts).get("/api/cohorts", params={"inn": "adalimumab"}).json()

    items = payload["items"]
    assert payload["total"] == 4
    assert len(items) == 4
    assert all("adalimumab" in item["inn_name"].lower() for item in items)
    expected = [asdict(cohort) for cohort in cohorts if "adalimumab" in cohort.inn_name.lower()]
    assert items == expected


def test_ac18_unfiltered_120_synthetic_cohorts_hold_one_page(
    use_cohorts: Callable[[list[Cohort]], TestClient], make_cohort: Callable[..., Cohort]
) -> None:
    """AC18: 120 cohorts without a filter give total 120 and 50 items."""
    payload = use_cohorts(synthetic_cohorts(make_cohort, 120)).get("/api/cohorts").json()

    assert payload["total"] == 120
    items = payload["items"]
    assert len(items) == 50
    assert items[0]["row_id"] == "CT0000_A1_001"
    assert items[-1]["row_id"] == "CT0049_A1_001"


def test_ac18_second_page_holds_the_51st_to_100th_cohort(
    use_cohorts: Callable[[list[Cohort]], TestClient], make_cohort: Callable[..., Cohort]
) -> None:
    """AC18: page 2 holds the next 50 cohorts and keeps the real total."""
    payload = (
        use_cohorts(synthetic_cohorts(make_cohort, 120))
        .get("/api/cohorts", params={"page": 2})
        .json()
    )

    assert payload["total"] == 120
    assert payload["page"] == 2
    assert payload["page_size"] == 50
    items = payload["items"]
    assert len(items) == 50
    assert items[0]["row_id"] == "CT0050_A1_001"
    assert items[-1]["row_id"] == "CT0099_A1_001"


def test_indication_and_route_filters_apply_to_the_json_interface(
    use_cohorts: Callable[[list[Cohort]], TestClient], make_cohort: Callable[..., Cohort]
) -> None:
    """The indication and route rules of the filter contract also hold for the API."""
    matching = synthetic_cohorts(
        make_cohort, 3, indication_category="Cancer and neoplasms", route="Subcutaneous"
    )
    decoys = [
        # Right route, wrong indication: fails if `indication` is ignored.
        make_cohort(
            row_id="DECOY1_A1_001",
            trial_id="DECOY1",
            indication_category="Healthy volunteers",
            route="Subcutaneous",
        ),
        # Right indication, wrong route: fails if `route` is ignored.
        make_cohort(
            row_id="DECOY2_A1_001",
            trial_id="DECOY2",
            indication_category="Cancer and neoplasms",
            route="Intravenous",
        ),
    ]

    payload = (
        use_cohorts([*matching, *decoys])
        .get(
            "/api/cohorts", params={"indication": " Cancer and neoplasms ", "route": "Subcutaneous"}
        )
        .json()
    )

    assert payload["total"] == 3
    assert [item["row_id"] for item in payload["items"]] == [cohort.row_id for cohort in matching]


def test_ac19_missing_values_are_json_null(
    use_cohorts: Callable[[list[Cohort]], TestClient], make_cohort: Callable[..., Cohort]
) -> None:
    """AC19: a missing ADA rate and ADA+ count are `null`, never 0 or a string."""
    cohort = make_cohort(n_ada_positive=None, ada_frequency_percent=None)
    response = use_cohorts([cohort]).get("/api/cohorts")

    item = response.json()["items"][0]
    assert item["n_ada_positive"] is None
    assert item["ada_frequency_percent"] is None
    assert '"n_ada_positive":null' in response.text
    assert '"ada_frequency_percent":null' in response.text


def test_numbers_are_served_as_loaded_without_rounding(
    use_cohorts: Callable[[list[Cohort]], TestClient], make_cohort: Callable[..., Cohort]
) -> None:
    """A non-whole ADA+ count and rate keep every digit; the HTML rounding does not apply."""
    cohort = make_cohort(n_ada_positive=41.76, ada_frequency_percent=2.36)
    response = use_cohorts([cohort]).get("/api/cohorts")

    item = response.json()["items"][0]
    assert item["n_ada_positive"] == 41.76
    assert item["ada_frequency_percent"] == 2.36
    assert '"n_ada_positive":41.76' in response.text
    assert '"ada_frequency_percent":2.36' in response.text
    assert "41.8" not in response.text


@pytest.mark.parametrize("query", ["page=0", "page=-1", "page=abc"])
def test_ac25_invalid_page_is_rejected_with_422(
    use_cohorts: Callable[[list[Cohort]], TestClient], cohorts_csv: Path, query: str
) -> None:
    """AC25: `page` below 1 or not an integer is answered with 422."""
    response = use_cohorts(load_cohorts(cohorts_csv)).get(f"/api/cohorts?{query}")

    assert response.status_code == 422


def test_ac25_page_size_is_fixed_and_cannot_be_set_by_the_client(
    use_cohorts: Callable[[list[Cohort]], TestClient], make_cohort: Callable[..., Cohort]
) -> None:
    """AC25: `page_size` is always 50, even when the client sends another value."""
    cohorts = synthetic_cohorts(make_cohort, 120)

    first = use_cohorts(cohorts).get("/api/cohorts", params={"page_size": 5}).json()
    assert first["page_size"] == 50
    assert len(first["items"]) == 50

    second = use_cohorts(cohorts).get("/api/cohorts", params={"page": 2, "page_size": 10}).json()
    assert second["page_size"] == 50
    assert len(second["items"]) == 50
    assert second["items"][0]["row_id"] == "CT0050_A1_001"


def test_ac22_json_interface_answers_503_with_the_detail_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC22 (JSON): no data file, fresh cache, no override: 503 with the exact body."""
    data_dir = tmp_path / "no-csv"
    data_dir.mkdir()
    monkeypatch.setenv("IDA_DATA_DIR", str(data_dir))
    reset_cohorts_cache()

    response = client.get("/api/cohorts")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Data not available"}
    # A JSON response is not a page: neither the HTML error page nor the notice.
    assert "<html" not in response.text
    assert "Immunogenicity Database Collaborative" not in response.text
    assert client.get("/health").status_code == 200
