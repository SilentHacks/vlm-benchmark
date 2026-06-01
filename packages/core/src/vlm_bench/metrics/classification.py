"""Classification accuracy and macro-F1 metrics."""

from __future__ import annotations

from vlm_bench.config import MetricConfig
from vlm_bench.metrics.base import MetricScore
from vlm_bench.metrics.label_match import LabelMatchMetric


class ClassificationMetric(LabelMatchMetric):
    def __init__(self, config: MetricConfig) -> None:
        super().__init__(config, normalize_labels=True)

    @staticmethod
    def aggregate(scores: list[MetricScore], mode: str = "accuracy") -> float:
        return LabelMatchMetric.aggregate(scores, mode=mode)
