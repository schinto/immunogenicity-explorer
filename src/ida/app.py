"""FastAPI application.

`GET /` renders the cohort table, `/health` is the liveness signal. The cohort
data is loaded lazily on the first request and only a successful result is kept
in the module-level cache (see the data access contract of spec 001).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ida import __version__
from ida.data import (
    PAGE_SIZE,
    DataFormatError,
    MissingColumnError,
    filter_cohorts,
    load_cohorts,
    paginate,
)
from ida.models import Cohort

logger = logging.getLogger(__name__)

#: Templates are found relative to `src/ida/`, not the working directory.
TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

DEFAULT_DATA_DIR = "data/idc"
DATA_FILE_NAME = "clinical_trials.csv"

#: The dash for a missing value (U+2013), never `0`, `None` or `nan`.
DASH = "\u2013"

app = FastAPI(title="Immunogenicity Explorer", version=__version__)

#: Successful load result, kept for the lifetime of the process.
_cohorts_cache: list[Cohort] | None = None


class DataUnavailableError(RuntimeError):
    """Raised when the cohort data cannot be loaded."""


def reset_cohorts_cache() -> None:
    """Empty the cohort cache; tests call it so every test starts fresh."""
    global _cohorts_cache
    _cohorts_cache = None


def _log_load_failure(error: Exception) -> None:
    """Log the exception type; its message only for the two safe error types.

    `MissingColumnError` and `DataFormatError` messages hold nothing but a
    column name and a row identifier. Every other message could contain row
    data, so only the type is logged.
    """
    if isinstance(error, (MissingColumnError, DataFormatError)):
        logger.error("Loading cohort data failed: %s: %s", type(error).__name__, error)
    else:
        logger.error("Loading cohort data failed: %s", type(error).__name__)


def get_cohorts() -> list[Cohort]:
    """Return the cohorts with a measured ADA value, loading them on first use.

    The file is `<IDA_DATA_DIR>/clinical_trials.csv`, with `IDA_DATA_DIR`
    defaulting to `data/idc`. Nothing is read at import time, and a failed load
    is not cached: the next request tries again.
    """
    global _cohorts_cache
    if _cohorts_cache is None:
        data_dir = Path(os.environ.get("IDA_DATA_DIR", DEFAULT_DATA_DIR))
        try:
            cohorts = load_cohorts(data_dir / DATA_FILE_NAME)
        except Exception as error:  # noqa: BLE001 - any load failure means 503
            _log_load_failure(error)
            raise DataUnavailableError("The cohort data is not available.") from error
        _cohorts_cache = cohorts
    return _cohorts_cache


def _or_dash(value: object) -> str:
    """Render a text cell; a missing value is the dash."""
    return DASH if value is None else str(value)


def _format_count(value: int | float | None) -> str:
    """Render a count: whole values as integers, non-whole ones with one decimal."""
    if value is None:
        return DASH
    if isinstance(value, float):
        return format(value, ".1f")
    return str(value)


def _format_rate(value: float | None) -> str:
    """Render an ADA rate in percent with one decimal, or the dash if missing."""
    return DASH if value is None else format(value, ".1f")


templates.env.filters["dash"] = _or_dash
templates.env.filters["count"] = _format_count
templates.env.filters["rate"] = _format_rate


@app.exception_handler(DataUnavailableError)
def data_unavailable(request: Request, exc: DataUnavailableError) -> HTMLResponse:
    """Answer 503 with an HTML page that carries footer and context notice."""
    return templates.TemplateResponse(
        request,
        "base.html",
        {"message": "Data not available"},
        status_code=503,
    )


def _navigation_query(filters: dict[str, str], destination: int) -> str:
    """Build a navigation link's query string from non-empty filters plus the page.

    `urlencode` keeps values with spaces, `&` or `#` intact; blank filters are
    left out, so only the page changes between the links.
    """
    params = {name: value for name, value in filters.items() if value}
    params["page"] = destination
    return "?" + urlencode(params)


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    cohorts: Annotated[list[Cohort], Depends(get_cohorts)],
    inn: str = "",
    indication: str = "",
    route: str = "",
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    """Render one page of the filtered cohort table."""
    filters = {
        "inn": inn.strip(),
        "indication": indication.strip(),
        "route": route.strip(),
    }
    filtered = filter_cohorts(cohorts, inn=inn, indication=indication, route=route)
    result = paginate(filtered, page)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "page": result,
            "filters": filters,
            "previous_url": _navigation_query(filters, page - 1) if page > 1 else None,
            "next_url": (
                _navigation_query(filters, page + 1) if page * PAGE_SIZE < result.total else None
            ),
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness signal for operations and acceptance tests."""
    return {"status": "ok", "version": __version__}
