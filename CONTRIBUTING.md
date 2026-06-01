# Contributing

Thanks for your interest in VLM Benchmark. This project is early-stage; focused contributions are welcome.

## Getting started

```bash
git clone https://github.com/SilentHacks/vlm-benchmark.git
cd vlm-benchmark
uv sync --all-packages
uv run pytest
```

For web changes:

```bash
cd packages/web && npm ci && npm run build
```

## Development workflow

1. Create a branch from `master`.
2. Make changes in the smallest package that owns the feature (`packages/core` for orchestration/metrics, `packages/api` for HTTP, `packages/cli` for CLI, `packages/web` for UI).
3. Add or update tests in `tests/` when behavior changes.
4. Run checks before opening a PR:

   ```bash
   uv run pytest
   uv run vlm-bench validate -c configs/example-bench.yaml
   cd packages/web && npm run build   # if you touched the web app
   ```

## Pull requests

- Keep PRs focused; one logical change per PR when possible.
- Describe what changed and how you tested it.
- Do not commit API keys, `.env` files, or local databases under `data/`.
- New metrics should register in `packages/core/src/vlm_bench/metrics/engine.py` and include a test in `tests/test_metrics.py`.

## Security

- Report security issues privately (open a GitHub Security Advisory or contact the maintainer) rather than filing a public issue for vulnerabilities.
- `custom_plugin` metrics execute arbitrary Python — only load plugins you trust.

## Code style

- Match existing patterns in the file you edit (type hints, async orchestration, Pydantic models).
- Prefer extending existing helpers over duplicating logic across CLI/API/web.
