"""Config and dataset validation utilities."""

from __future__ import annotations

from pathlib import Path

from vlm_bench.config import BenchmarkConfig
from vlm_bench.dataset import load_manifest
from vlm_bench.metrics.engine import create_scorer


def validate_config(config: BenchmarkConfig, config_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    manifest_path = config.resolve_manifest_path(config_path)
    if not manifest_path.exists():
        errors.append(f"Manifest not found: {manifest_path}")
    else:
        try:
            rows = load_manifest(manifest_path, config.resolve_base_dir(config_path))
            if not rows:
                errors.append("Manifest is empty")
            for row in rows:
                if not Path(row.path).exists():
                    errors.append(f"Image not found: {row.path} (image_id={row.image_id})")
        except Exception as e:
            errors.append(f"Failed to load manifest: {e}")

    if not config.models:
        errors.append("No models configured")

    if not config.prompts.user and not config.prompts.system:
        errors.append("At least one prompt (system or user) is required")

    try:
        project_root = config_path.parent.parent if config_path else Path.cwd()
        if config_path and not (project_root / "fixtures").exists():
            project_root = config_path.parent
        create_scorer(config.metric, project_root)
    except Exception as e:
        errors.append(f"Invalid metric config: {e}")

    return errors
