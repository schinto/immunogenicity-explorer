"""Rauchtest des Grundgerüsts."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ida.app import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_fixtures_are_present(cohorts_csv: Path, therapeutics_csv: Path) -> None:
    assert cohorts_csv.is_file()
    assert therapeutics_csv.is_file()
    assert cohorts_csv.read_text(encoding="utf-8").startswith("IDC Row identifier,")
