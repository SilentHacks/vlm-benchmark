"""Contains keywords rubric metric."""

from __future__ import annotations

from vlm_bench.config import MetricConfig
from vlm_bench.metrics.base import MetricScore, ScoreContext


class ContainsKeywordsMetric:
    def __init__(self, config: MetricConfig) -> None:
        self.config = config

    def score(self, ctx: ScoreContext) -> MetricScore:
        text = ctx.response.lower()
        keywords = self.config.keywords
        if not keywords:
            return MetricScore(score=0.0, passed=False, details={"error": "no keywords configured"})
        found = [kw for kw in keywords if kw.lower() in text]
        if self.config.match_mode == "all":
            passed = len(found) == len(keywords)
        else:
            passed = len(found) > 0
        score = len(found) / len(keywords)
        return MetricScore(
            score=score,
            passed=passed,
            details={"found": found, "missing": [k for k in keywords if k not in found]},
        )
