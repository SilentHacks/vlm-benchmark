"""Regex rubric metric."""

from __future__ import annotations

import re

from vlm_bench.config import MetricConfig
from vlm_bench.metrics.base import MetricScore, ScoreContext


class RegexMetric:
    def __init__(self, config: MetricConfig) -> None:
        self.config = config

    def score(self, ctx: ScoreContext) -> MetricScore:
        pattern = self.config.pattern
        if not pattern:
            return MetricScore(score=0.0, passed=False, details={"error": "no pattern configured"})
        match = re.search(pattern, ctx.response, re.IGNORECASE | re.DOTALL)
        passed = match is not None
        details: dict = {"pattern": pattern}
        if match:
            details["match"] = match.group(0)
        return MetricScore(score=1.0 if passed else 0.0, passed=passed, details=details)
