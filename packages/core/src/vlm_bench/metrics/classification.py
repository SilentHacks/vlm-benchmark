"""Classification accuracy and macro-F1 metrics."""

from __future__ import annotations

from vlm_bench.config import MetricConfig
from vlm_bench.metrics.base import MetricScore, ScoreContext
from vlm_bench.metrics.parse import normalize, parse_response


class ClassificationMetric:
    def __init__(self, config: MetricConfig) -> None:
        self.config = config

    def score(self, ctx: ScoreContext) -> MetricScore:
        if ctx.ground_truth is None or not self.config.labels_field:
            return MetricScore(score=0.0, passed=False, details={"error": "missing ground truth"})
        expected = normalize(ctx.ground_truth.get_label(self.config.labels_field))
        parsed = normalize(parse_response(ctx.response, self.config.parse))
        match = expected == parsed
        return MetricScore(
            score=1.0 if match else 0.0,
            passed=match,
            details={"expected": expected, "actual": parsed},
        )

    @staticmethod
    def aggregate(scores: list[MetricScore], mode: str = "accuracy") -> float:
        if not scores:
            return 0.0
        if mode == "accuracy":
            return sum(s.score for s in scores) / len(scores)
        if mode == "macro_f1":
            from sklearn.metrics import f1_score

            y_true = [s.details.get("expected", "") for s in scores]
            y_pred = [s.details.get("actual", "") for s in scores]
            labels = sorted(set(y_true) | set(y_pred))
            if not labels:
                return 0.0
            return float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
        return sum(s.score for s in scores) / len(scores)
