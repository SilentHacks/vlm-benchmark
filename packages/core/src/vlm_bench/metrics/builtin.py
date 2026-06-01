"""Built-in metric scorers."""

from __future__ import annotations

import json
import re
from typing import Any

import jsonschema
from sklearn.metrics import accuracy_score, f1_score

from vlm_bench.config import MetricConfig
from vlm_bench.metrics.base import ImageContext, MetricScore, MetricScorer, normalize_text, parse_response
from vlm_bench.metrics.plugins import load_custom_plugin


class ExactMatchScorer:
    def score(
        self, ctx: ImageContext, response: str, ground_truth: Any | None = None
    ) -> MetricScore:
        if ground_truth is None:
            return MetricScore(0.0, False, {"error": "no ground truth"})
        expected = normalize_text(str(ground_truth))
        actual = normalize_text(response)
        passed = expected == actual
        return MetricScore(1.0 if passed else 0.0, passed, {"expected": expected, "actual": actual})


class ClassificationScorer:
    def __init__(self, config: MetricConfig) -> None:
        self._config = config
        self._labels: list[str] = []

    def score(
        self, ctx: ImageContext, response: str, ground_truth: Any | None = None
    ) -> MetricScore:
        if ground_truth is None:
            return MetricScore(0.0, False, {"error": "no ground truth"})
        parsed = parse_response(response, self._config.parse) if self._config.parse else response
        expected = normalize_text(str(ground_truth))
        actual = normalize_text(str(parsed))
        passed = expected == actual
        return MetricScore(1.0 if passed else 0.0, passed, {"expected": expected, "actual": actual})

    def aggregate(self, y_true: list[str], y_pred: list[str]) -> dict[str, float]:
        if not y_true:
            return {"accuracy": 0.0, "macro_f1": 0.0}
        labels = sorted(set(y_true) | set(y_pred))
        acc = accuracy_score(y_true, y_pred)
        try:
            f1 = f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)
        except ValueError:
            f1 = 0.0
        return {"accuracy": float(acc), "macro_f1": float(f1)}


class JsonFieldMatchScorer:
    def __init__(self, config: MetricConfig) -> None:
        self._fields = config.fields or []

    def score(
        self, ctx: ImageContext, response: str, ground_truth: Any | None = None
    ) -> MetricScore:
        try:
            data = json.loads(response) if response.strip().startswith("{") else {}
        except json.JSONDecodeError:
            return MetricScore(0.0, False, {"error": "invalid json"})
        matches = []
        for field_def in self._fields:
            if hasattr(field_def, "model_dump"):
                field_def = field_def.model_dump()
            name = field_def.get("name", "")
            expected_key = field_def.get("expected", f"expected_{name}")
            expected = ctx.manifest_row.get(expected_key, field_def.get("value"))
            actual = data.get(name)
            ok = actual == expected or str(actual) == str(expected)
            matches.append(ok)
        if not matches:
            return MetricScore(0.0, False, {"error": "no fields configured"})
        score = sum(matches) / len(matches)
        passed = all(matches)
        return MetricScore(score, passed, {"field_results": matches})


class ContainsKeywordsScorer:
    def __init__(self, config: MetricConfig) -> None:
        self._keywords = [k.lower() for k in (config.keywords or [])]
        self._mode = config.match_mode

    def score(
        self, ctx: ImageContext, response: str, ground_truth: Any | None = None
    ) -> MetricScore:
        text = response.lower()
        if not self._keywords:
            return MetricScore(0.0, False, {"error": "no keywords"})
        found = [k for k in self._keywords if k in text]
        if self._mode == "any":
            passed = len(found) > 0
        else:
            passed = len(found) == len(self._keywords)
        score = len(found) / len(self._keywords)
        return MetricScore(score, passed, {"found": found})


class RegexScorer:
    def __init__(self, config: MetricConfig) -> None:
        self._pattern = config.pattern or ".*"

    def score(
        self, ctx: ImageContext, response: str, ground_truth: Any | None = None
    ) -> MetricScore:
        passed = bool(re.search(self._pattern, response, re.IGNORECASE | re.DOTALL))
        return MetricScore(1.0 if passed else 0.0, passed, {"pattern": self._pattern})


class JsonSchemaScorer:
    def __init__(self, config: MetricConfig) -> None:
        self._schema = config.schema or {}

    def score(
        self, ctx: ImageContext, response: str, ground_truth: Any | None = None
    ) -> MetricScore:
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            return MetricScore(0.0, False, {"error": str(e)})
        try:
            jsonschema.validate(data, self._schema)
            return MetricScore(1.0, True, {})
        except jsonschema.ValidationError as e:
            return MetricScore(0.0, False, {"error": e.message})


def get_scorer(config: MetricConfig, plugins_dir: str | None = None) -> MetricScorer:
    t = config.type
    if t == "exact_match":
        return ExactMatchScorer()
    if t == "classification":
        return ClassificationScorer(config)
    if t == "json_field_match":
        return JsonFieldMatchScorer(config)
    if t == "contains_keywords":
        return ContainsKeywordsScorer(config)
    if t == "regex":
        return RegexScorer(config)
    if t == "json_schema":
        return JsonSchemaScorer(config)
    if t == "custom_plugin" and config.plugin:
        return load_custom_plugin(config.plugin, plugins_dir)
    raise ValueError(f"Unknown metric type: {t}")
