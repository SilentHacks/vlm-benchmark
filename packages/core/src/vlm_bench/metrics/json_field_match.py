"""JSON field match metric."""

from __future__ import annotations

import json

from vlm_bench.config import MetricConfig
from vlm_bench.metrics.base import MetricScore, ScoreContext
from vlm_bench.metrics.parse import normalize, parse_response


class JsonFieldMatchMetric:
    def __init__(self, config: MetricConfig) -> None:
        self.config = config

    def score(self, ctx: ScoreContext) -> MetricScore:
        parsed = parse_response(ctx.response, self.config.parse)
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except json.JSONDecodeError:
                return MetricScore(
                    score=0.0,
                    passed=False,
                    details={"error": "invalid JSON", "raw": ctx.response[:200]},
                )
        if not isinstance(parsed, dict):
            return MetricScore(score=0.0, passed=False, details={"error": "expected JSON object"})

        field_results: dict[str, dict] = {}
        total = 0
        correct = 0
        for field_cfg in self.config.fields:
            total += 1
            actual = parsed.get(field_cfg.name)
            if ctx.ground_truth and field_cfg.expected:
                expected_raw = ctx.ground_truth.get_label(field_cfg.expected)
            else:
                expected_raw = field_cfg.expected
            exp_norm = normalize(expected_raw)
            act_norm = normalize(actual)
            match = exp_norm == act_norm
            if match:
                correct += 1
            field_results[field_cfg.name] = {
                "expected": expected_raw,
                "actual": actual,
                "match": match,
            }

        score = correct / total if total else 0.0
        return MetricScore(
            score=score,
            passed=score == 1.0,
            details={"fields": field_results, "correct": correct, "total": total},
        )
