"""Exact match metric."""

from __future__ import annotations

from vlm_bench.config import MetricConfig
from vlm_bench.metrics.base import MetricScore, ScoreContext
from vlm_bench.metrics.parse import normalize, parse_response


class ExactMatchMetric:
    def __init__(self, config: MetricConfig) -> None:
        self.config = config

    def score(self, ctx: ScoreContext) -> MetricScore:
        if ctx.ground_truth is None or not self.config.labels_field:
            return MetricScore(score=0.0, passed=False, details={"error": "missing ground truth"})
        expected = ctx.ground_truth.get_label(self.config.labels_field)
        parsed = parse_response(ctx.response, self.config.parse)
        match = normalize(parsed) == normalize(expected)
        return MetricScore(
            score=1.0 if match else 0.0,
            passed=match,
            details={"expected": expected, "actual": parsed},
        )
