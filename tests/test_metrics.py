"""Unit tests for metric scorers."""

import json

from vlm_bench.config import MetricConfig, MetricParseConfig
from vlm_bench.metrics.base import ScoreContext
from vlm_bench.metrics.classification import ClassificationMetric
from vlm_bench.metrics.contains_keywords import ContainsKeywordsMetric
from vlm_bench.metrics.exact_match import ExactMatchMetric
from vlm_bench.metrics.json_field_match import JsonFieldMatchMetric
from vlm_bench.metrics.json_schema import JsonSchemaMetric
from vlm_bench.metrics.regex import RegexMetric
from vlm_bench.config import ManifestRow


def _ctx(row: dict | None = None) -> ScoreContext:
    r = ManifestRow.model_validate(
        {"image_id": "t1", "path": "x.png", "expected_class": "cat", **(row or {})}
    )
    return ScoreContext(
        image_id="t1",
        prompt_system="",
        prompt_user="",
        response="",
        ground_truth=r,
        metric_config=MetricConfig(type="classification"),
    )


def test_exact_match_pass():
    ctx = _ctx()
    ctx.response = "Cat"
    s = ExactMatchMetric(MetricConfig(type="exact_match", labels_field="expected_class"))
    r = s.score(ctx)
    assert r.passed and r.score == 1.0


def test_classification_json_parse():
    cfg = MetricConfig(
        type="classification",
        parse=MetricParseConfig(mode="json", path="$.label"),
        labels_field="expected_class",
    )
    ctx = _ctx({"expected_class": "cat"})
    ctx.response = json.dumps({"label": "cat", "confidence": 0.9})
    r = ClassificationMetric(cfg).score(ctx)
    assert r.passed


def test_json_field_match():
    cfg = MetricConfig(
        type="json_field_match",
        fields=[{"name": "defect", "expected": "expected_class"}],
    )
    row = ManifestRow.model_validate(
        {"image_id": "t1", "path": "x.png", "expected_class": True}
    )
    ctx = ScoreContext(
        image_id="t1",
        prompt_system="",
        prompt_user="",
        response=json.dumps({"defect": True}),
        ground_truth=row,
        metric_config=cfg,
    )
    r = JsonFieldMatchMetric(cfg).score(ctx)
    assert r.passed


def test_contains_keywords_all():
    cfg = MetricConfig(
        type="contains_keywords",
        keywords=["hello", "world"],
        match_mode="all",
    )
    ctx = _ctx()
    ctx.response = "Hello beautiful world"
    assert ContainsKeywordsMetric(cfg).score(ctx).passed


def test_regex():
    cfg = MetricConfig(type="regex", pattern=r"\d+\.\d+")
    ctx = _ctx()
    ctx.response = "score is 0.95"
    assert RegexMetric(cfg).score(ctx).passed


def test_json_schema():
    schema = {
        "type": "object",
        "required": ["label"],
        "properties": {"label": {"type": "string"}},
    }
    cfg = MetricConfig(type="json_schema", schema=schema)
    ctx = _ctx()
    ctx.response = json.dumps({"label": "cat"})
    assert JsonSchemaMetric(cfg).score(ctx).passed
