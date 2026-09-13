FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml requirements.txt README.md ./
COPY src ./src
COPY configs ./configs
COPY web ./web
COPY run_api.py ./

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir . \
    && groupadd --system xaita \
    && useradd --system --gid xaita --home-dir /app --no-create-home xaita \
    && chown -R xaita:xaita /app

USER xaita

EXPOSE 8080

CMD ["python", "run_api.py"]
