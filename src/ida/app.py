"""FastAPI-Anwendung.

Grundgerüst. Die Endpunkte der Oberfläche entstehen pro Spec unter specs/.
"""

from __future__ import annotations

from fastapi import FastAPI

from ida import __version__

app = FastAPI(title="Immunogenicity Explorer", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    """Lebenszeichen für Betrieb und Abnahmetests."""
    return {"status": "ok", "version": __version__}
