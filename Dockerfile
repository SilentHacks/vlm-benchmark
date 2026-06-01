FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock* ./
COPY packages/core packages/core
COPY packages/api packages/api
COPY packages/cli packages/cli
COPY configs configs
COPY fixtures fixtures
COPY schemas schemas
COPY metrics metrics

RUN uv sync --frozen 2>/dev/null || uv sync

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "vlm_bench_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
