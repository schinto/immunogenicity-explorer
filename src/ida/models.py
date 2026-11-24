"""Data models for the immunogenicity explorer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cohort:
    """One cohort with a measured ADA value.

    The fields map to the columns of `clinical_trials.csv`. Missing values are
    `None`, never 0.
    """

    row_id: str | None
    trial_id: str | None
    inn_name: str | None
    indication_category: str | None
    route: str | None
    n_analyzed: int | None
    n_ada_positive: int | None
    ada_frequency_percent: float | None
