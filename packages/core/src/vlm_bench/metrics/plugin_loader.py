"""Custom metric plugin loader."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from vlm_bench.metrics.base import MetricScorer, MetricScore, ScoreContext


class PluginMetric:
    def __init__(self, module: ModuleType) -> None:
        if not hasattr(module, "score"):
            raise ValueError("Plugin must define score(image_ctx, response, ground_truth) function")
        self._score_fn = module.score

    def score(self, ctx: ScoreContext) -> MetricScore:
        gt = None
        if ctx.ground_truth:
            gt = ctx.ground_truth.model_dump()
        result = self._score_fn(
            {
                "image_id": ctx.image_id,
                "prompt_system": ctx.prompt_system,
                "prompt_user": ctx.prompt_user,
            },
            ctx.response,
            gt,
        )
        if isinstance(result, MetricScore):
            return result
        if isinstance(result, dict):
            return MetricScore(
                score=float(result.get("score", 0)),
                passed=bool(result.get("passed", False)),
                details=result.get("details", {}),
            )
        raise ValueError("Plugin score() must return MetricScore or dict")


def load_plugin(path: str | Path) -> MetricScorer:
    plugin_path = Path(path)
    if not plugin_path.is_absolute():
        plugin_path = plugin_path.resolve()
    spec = importlib.util.spec_from_file_location(f"metric_plugin_{plugin_path.stem}", plugin_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load plugin from {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return PluginMetric(module)


def resolve_plugin_path(plugin: str, project_root: Path | None = None) -> Path:
    path = Path(plugin)
    if path.is_absolute():
        return path
    if project_root:
        candidate = project_root / path
        if candidate.exists():
            return candidate
    return Path.cwd() / path
