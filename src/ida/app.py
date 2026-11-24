"""FastAPI application.

Skeleton. The UI endpoints are added per spec under specs/.
"""

from __future__ import annotations

from fastapi import FastAPI

from ida import __version__

app = FastAPI(title="Immunogenicity Explorer", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness signal for operations and acceptance tests."""
    return {"status": "ok", "version": __version__}
