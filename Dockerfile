FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml requirements.txt README.md ./
COPY src ./src
COPY configs ./configs
COPY web ./web
COPY scripts ./scripts
COPY run_api.py ./

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir . \
    && groupadd --system xaita \
    && useradd --system --gid xaita --home-dir /app --no-create-home xaita \
    && mkdir -p /app/data/raw/batadal \
    && chown -R xaita:xaita /app

USER xaita

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4)" || exit 1

CMD ["sh", "-c", "python scripts/prepare_runtime_data.py && python run_api.py"]
