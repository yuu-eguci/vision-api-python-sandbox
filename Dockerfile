# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

FROM python:3.15.0-slim-trixie@sha256:f5b92f2a669a4c347044f29367f31983280b648250ca94dea66f98c53bc87e58 AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH
RUN useradd --create-home --uid 1000 app

# 依存を先に入れて、ソース変更時のビルドを速くする
FROM base AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

# lint・型チェック・テスト用
FROM builder AS dev
RUN uv sync --locked --no-install-project
COPY tests ./tests
RUN uv sync --locked && chown -R app:app /app
USER app
CMD ["sh", "-c", "ruff check . && ruff format --check . && mypy && pytest"]

# 実行用。仮想環境だけを持ち込む
FROM base AS runtime
COPY --from=builder /opt/venv /opt/venv
WORKDIR /work
USER app
ENTRYPOINT ["vision-sandbox"]
