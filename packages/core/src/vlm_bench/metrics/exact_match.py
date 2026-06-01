"""Exact match metric."""

from __future__ import annotations

from vlm_bench.config import MetricConfig
from vlm_bench.metrics.base import MetricScore, ScoreContext
from vlm_bench.metrics.label_match import LabelMatchMetric


class ExactMatchMetric(LabelMatchMetric):
    def __init__(self, config: MetricConfig) -> None:
        super().__init__(config, normalize_labels=True)

    def score(self, ctx: ScoreContext) -> MetricScore:
        return super().score(ctx)
