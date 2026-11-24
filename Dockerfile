# Runtime image for public operation at adam.entreater.com
#
# The dataset is baked in at build time and verified via SHA-256
# (scripts/fetch_data.py). The image is therefore immutable and needs no network
# at runtime. Data license: CC BY 4.0, see DATA.md.
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    IDA_DATA_DIR=/app/data/idc

WORKDIR /app

# Dependencies first, so the Docker layer is kept on code changes
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Bake in the dataset (network only at build time, fixed checksums)
COPY scripts ./scripts
COPY DATA.md ./
RUN python scripts/fetch_data.py

# Run without root privileges
RUN useradd --system --create-home --uid 10001 ida && chown -R ida:ida /app
USER ida

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]

CMD ["uvicorn", "ida.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
