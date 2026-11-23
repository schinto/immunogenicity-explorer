# Laufzeit-Abbild für den öffentlichen Betrieb unter adam.entreater.com
#
# Der Datensatz wird beim Bauen eingebacken und dabei über SHA-256 geprüft
# (scripts/fetch_data.py). Das Abbild ist damit unveränderlich und braucht zur
# Laufzeit kein Netz. Lizenz der Daten: CC BY 4.0, siehe DATA.md.
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    IDA_DATA_DIR=/app/data/idc

WORKDIR /app

# Abhängigkeiten zuerst, damit die Docker-Schicht beim Codeänderungen erhalten bleibt
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Datensatz einbacken (Netz nur beim Bauen, Prüfsummen fest)
COPY scripts ./scripts
COPY DATA.md ./
RUN python scripts/fetch_data.py

# Ohne Rootrechte betreiben
RUN useradd --system --create-home --uid 10001 ida && chown -R ida:ida /app
USER ida

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]

CMD ["uvicorn", "ida.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
