FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml requirements.txt README.md ./
COPY src ./src
COPY configs ./configs
COPY web ./web
COPY scripts ./scripts
COPY run_api.py ./

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpcre2-8-0 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir . \
    && pip uninstall -y setuptools msgpack urllib3 || true \
    && rm -rf /usr/local/lib/python3.12/site-packages/setuptools* /usr/local/lib/python3.12/site-packages/msgpack* /usr/local/lib/python3.12/site-packages/urllib3* \
    && pip install --no-cache-dir "setuptools>=78.1.1" "msgpack>=1.2.1" "urllib3>=2.8.0" \
    && python -c "import importlib.metadata as m; assert tuple(map(int, m.version('setuptools').split('.')[:2])) >= (78,1); assert tuple(map(int, m.version('msgpack').split('.')[:2])) >= (1,2); assert tuple(map(int, m.version('urllib3').split('.')[:2])) >= (2,8)" \
    && groupadd --system xaita \
    && useradd --system --gid xaita --home-dir /app --no-create-home xaita \
    && mkdir -p /app/data/raw/batadal \
    && chown -R xaita:xaita /app

USER xaita

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4)" || exit 1

CMD ["sh", "-c", "python scripts/prepare_runtime_data.py && python run_api.py"]
