"""Unified path resolution for benchmark configs."""

from __future__ import annotations

from pathlib import Path

from vlm_bench.config import BenchmarkConfig


def resolve_paths(
    config: BenchmarkConfig,
    *,
    config_path: Path | None = None,
    project_root: Path | None = None,
) -> tuple[Path, Path]:
    """Return (manifest_path, base_dir) under project_root when possible."""
    root = project_root or (config_path.parent if config_path else Path.cwd())
    manifest = config.resolve_manifest_path(config_path)
    if not manifest.is_absolute():
        candidate = (root / manifest).resolve()
        if candidate.exists():
            manifest = candidate
    base_dir = config.resolve_base_dir(config_path)
    if not base_dir.is_absolute():
        candidate = (root / base_dir).resolve()
        if candidate.exists():
            base_dir = candidate
    return manifest, base_dir
