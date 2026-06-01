"""Metric engine: scorer factory and aggregation."""

from __future__ import annotations

from pathlib import Path

from vlm_bench.config import BenchmarkConfig, ManifestRow, MetricConfig
from vlm_bench.metrics.base import MetricScore, MetricScorer, ScoreContext
from vlm_bench.metrics.classification import ClassificationMetric
from vlm_bench.metrics.contains_keywords import ContainsKeywordsMetric
from vlm_bench.metrics.exact_match import ExactMatchMetric
from vlm_bench.metrics.json_field_match import JsonFieldMatchMetric
from vlm_bench.metrics.json_schema import JsonSchemaMetric
from vlm_bench.metrics.plugin_loader import load_plugin, resolve_plugin_path
from vlm_bench.metrics.regex import RegexMetric


def create_scorer(config: MetricConfig, project_root: Path | None = None) -> MetricScorer:
    metric_type = config.type
    if metric_type == "exact_match":
        return ExactMatchMetric(config)
    if metric_type == "classification":
        return ClassificationMetric(config)
    if metric_type == "json_field_match":
        return JsonFieldMatchMetric(config)
    if metric_type == "contains_keywords":
        return ContainsKeywordsMetric(config)
    if metric_type == "regex":
        return RegexMetric(config)
    if metric_type == "json_schema":
        return JsonSchemaMetric(config)
    if metric_type in ("custom_plugin", "plugin"):
        if not config.plugin:
            raise ValueError("custom_plugin metric requires 'plugin' path")
        plugin_path = resolve_plugin_path(config.plugin, project_root)
        return load_plugin(plugin_path)
    raise ValueError(f"Unknown metric type: {metric_type}")


class MetricEngine:
    def __init__(self, config: BenchmarkConfig, project_root: Path | None = None) -> None:
        self.config = config
        self.scorer = create_scorer(config.metric, project_root)

    def score(
        self,
        *,
        image_id: str,
        response: str,
        ground_truth: ManifestRow | None,
        prompt_system: str = "",
        prompt_user: str = "",
    ) -> MetricScore:
        ctx = ScoreContext(
            image_id=image_id,
            prompt_system=prompt_system,
            prompt_user=prompt_user,
            response=response,
            ground_truth=ground_truth,
            metric_config=self.config.metric,
        )
        return self.scorer.score(ctx)

    def aggregate(self, scores: list[MetricScore]) -> float:
        if not scores:
            return 0.0
        mode = self.config.metric.aggregate
        if mode == "macro_f1" and isinstance(self.scorer, ClassificationMetric):
            return ClassificationMetric.aggregate(scores, mode="macro_f1")
        return sum(s.score for s in scores) / len(scores)
