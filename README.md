# VLM Benchmark

Compare vision-language models on datasets with pluggable metrics, cost tracking, and a web dashboard.

## Quick Start

```bash
# Install Python dependencies
cd vlm-benchmark
uv sync

# Validate config
uv run vlm-bench validate -c configs/example-bench.yaml

# Run benchmark (uses mock adapter by default — no API keys needed)
uv run vlm-bench run -c configs/example-bench.yaml

# View results
uv run vlm-bench results <RUN_ID> --format table

# Export HTML report
uv run vlm-bench export <RUN_ID> --out report.html --format html
```

## Web Dashboard

```bash
# Terminal 1: API server
uv run uvicorn vlm_bench_api.main:app --reload --port 8000

# Terminal 2: Web UI
cd packages/web && npm install && npm run dev
```

Open http://localhost:5173

## Architecture

```
vlm-benchmark/
├── packages/core/          # vlm_bench — orchestrator, adapters, metrics, cache
├── packages/api/           # FastAPI REST + SSE
├── packages/cli/           # Typer CLI (vlm-bench)
├── packages/web/           # React + Vite dashboard
├── configs/                # Example benchmark YAML
├── metrics/plugins/        # Custom metric plugins
├── schemas/                # JSON schemas
└── fixtures/               # Sample dataset (3 images + manifest)
```

## Supported Models

| Provider | Model ID | Env Var |
|----------|----------|---------|
| Mock | `mock:deterministic` | — |
| OpenAI | `openai:gpt-4o` | `OPENAI_API_KEY` |
| Google | `google:gemini-2.0-flash` | `GOOGLE_API_KEY` |
| Anthropic | `anthropic:claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` |

## Metrics

- **exact_match** — normalized string match
- **classification** — accuracy / macro-F1
- **json_field_match** — per-field JSON equality
- **contains_keywords** — keyword presence (all/any)
- **regex** — pattern match
- **json_schema** — JSON Schema validation
- **custom_plugin** — drop-in Python module

## CI

```bash
uv run pytest
uv run vlm-bench validate -c configs/example-bench.yaml
```

GitHub Actions runs pytest, config validation, golden mock run, and web build on every push.

## License

MIT
