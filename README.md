# VLM Benchmark

[![CI](https://github.com/SilentHacks/vlm-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/SilentHacks/vlm-benchmark/actions/workflows/ci.yml)

Benchmark and compare vision-language models (VLMs) on image datasets with pluggable metrics, token cost tracking, and a web dashboard.

Works out of the box with a **mock adapter** (no API keys). Swap in OpenAI, Google Gemini, or Anthropic models via YAML config.

## Features

- **Multi-provider adapters** — mock, OpenAI, Gemini, Anthropic
- **Pluggable metrics** — classification, exact match, JSON field match, regex, keywords, JSON Schema, custom Python plugins (CLI only)
- **Async orchestration** — configurable concurrency, retries, inference cache
- **Cost & latency** — per-model aggregates with pricing from `configs/pricing.yaml`
- **CLI** — validate, run, inspect results, export HTML reports
- **REST API + SSE** — start runs, stream progress, fetch results
- **React dashboard** — wizard, live run view, leaderboard, per-image comparison

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Node.js 20+ (web UI only)

## Quick start

```bash
git clone https://github.com/SilentHacks/vlm-benchmark.git
cd vlm-benchmark

uv sync --all-packages

# Validate example config
uv run vlm-bench validate -c configs/example-bench.yaml

# Run benchmark (mock adapter — no API keys)
uv run vlm-bench run -c configs/example-bench.yaml

# View results (use RUN_ID from output)
uv run vlm-bench results <RUN_ID> --format table

# Export HTML report
uv run vlm-bench export <RUN_ID> --out report.html --format html
```

## Live model providers

Set environment variables (see [`.env.example`](.env.example)):

| Provider | Model ID example | Env var |
|----------|------------------|---------|
| Mock | `mock:deterministic` | — |
| OpenAI | `openai:gpt-4o` | `OPENAI_API_KEY` |
| Google | `google:gemini-2.0-flash` | `GOOGLE_API_KEY` |
| Anthropic | `anthropic:claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` |

Edit `configs/example-bench.yaml` and replace `models` with your provider IDs.

## Web dashboard

```bash
# Terminal 1 — API (bind localhost for local dev)
uv run uvicorn vlm_bench_api.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — UI
cd packages/web && npm ci && npm run dev
```

Open http://localhost:5173

## Docker

```bash
# Optional: copy .env.example to .env and add API keys for live models
docker compose up --build
```

- API: http://localhost:8000  
- Web: http://localhost:5173  

## Project layout

```
vlm-benchmark/
├── packages/core/     # Orchestrator, adapters, metrics, SQLite storage
├── packages/api/      # FastAPI REST + SSE
├── packages/cli/      # Typer CLI (`vlm-bench`)
├── packages/web/      # React + Vite dashboard
├── configs/           # Example benchmark + pricing YAML
├── metrics/plugins/   # Custom metric plugins
├── schemas/           # JSON Schema for config and results
├── fixtures/          # Sample dataset (3 images)
└── tests/             # Pytest suite
```

## Metrics

| Type | Description |
|------|-------------|
| `exact_match` | Normalized string match |
| `classification` | Label match; aggregate `accuracy` or `macro_f1` |
| `json_field_match` | Per-field JSON equality |
| `contains_keywords` | Keyword presence (all/any) |
| `regex` | Pattern match |
| `json_schema` | JSON Schema validation |
| `custom_plugin` | Python module (CLI only) |

## Configuration

Benchmarks are defined in YAML. See [`configs/example-bench.yaml`](configs/example-bench.yaml). Validate before running:

```bash
uv run vlm-bench validate -c path/to/bench.yaml
```

Optional `fail_under` in config exits non-zero (CLI) or marks the run failed (API) when the best model score is below the threshold.

## Development

```bash
uv sync --all-packages
uv run pytest
uv run vlm-bench validate -c configs/example-bench.yaml
cd packages/web && npm ci && npm run build
```

CI runs on push: pytest, config validation, web build, and API Docker image build.

## Security

- The API has **no authentication**. Use `127.0.0.1` for local development; do not expose on untrusted networks without a reverse proxy.
- `custom_plugin` metrics execute arbitrary Python from disk — **CLI only**; HTTP `POST /runs` rejects plugin metrics.
- Config and thumbnail paths are jailed under the project root.
- Never commit `.env` or API keys. Use environment variables only.

## License

MIT — see [LICENSE](LICENSE).
