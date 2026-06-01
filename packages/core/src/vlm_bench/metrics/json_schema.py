"""JSON schema validation rubric metric."""

from __future__ import annotations

import json

import jsonschema

from vlm_bench.config import MetricConfig
from vlm_bench.metrics.base import MetricScore, ScoreContext
from vlm_bench.metrics.parse import parse_response


class JsonSchemaMetric:
    def __init__(self, config: MetricConfig) -> None:
        self.config = config

    def score(self, ctx: ScoreContext) -> MetricScore:
        schema = self.config.validation_schema
        if not schema:
            return MetricScore(score=0.0, passed=False, details={"error": "no schema configured"})
        parsed = parse_response(ctx.response, self.config.parse)
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except json.JSONDecodeError as e:
                return MetricScore(score=0.0, passed=False, details={"error": str(e)})
        try:
            jsonschema.validate(parsed, schema)
            return MetricScore(score=1.0, passed=True, details={"valid": True})
        except jsonschema.ValidationError as e:
            return MetricScore(score=0.0, passed=False, details={"error": e.message})
