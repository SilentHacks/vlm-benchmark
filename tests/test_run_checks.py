"""Run post-check helpers."""

import json
from pathlib import Path

import jsonschema

from vlm_bench.config import BenchmarkConfig
from vlm_bench.run_checks import best_primary_score, check_fail_under

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "run-results.schema.json"


def test_check_fail_under_pass():
    cfg = BenchmarkConfig.model_validate(
        {
            "name": "t",
            "prompts": {"system": "", "user": "u"},
            "dataset": {"manifest": "fixtures/manifest.jsonl", "base_dir": "fixtures"},
            "models": ["mock:deterministic"],
            "metric": {"type": "classification", "labels_field": "expected_class"},
            "fail_under": 0.5,
        }
    )
    passed, best, threshold = check_fail_under(
        cfg, {"by_model": {"mock:deterministic": {"primary_score": 0.9}}}
    )
    assert passed
    assert best == 0.9
    assert threshold == 0.5


def test_check_fail_under_fail():
    cfg = BenchmarkConfig.model_validate(
        {
            "name": "t",
            "prompts": {"system": "", "user": "u"},
            "dataset": {"manifest": "fixtures/manifest.jsonl", "base_dir": "fixtures"},
            "models": ["mock:deterministic"],
            "metric": {"type": "classification", "labels_field": "expected_class"},
            "fail_under": 0.99,
        }
    )
    passed, best, _ = check_fail_under(
        cfg, {"by_model": {"mock:deterministic": {"primary_score": 0.5}}}
    )
    assert not passed
    assert best == 0.5


def test_run_results_schema_shape():
    aggregates = {
        "run_id": "abc123",
        "by_model": {
            "mock:deterministic": {
                "primary_score": 1.0,
                "latency_ms": {"p50": 10.0, "p95": 20.0},
                "cost_usd": 0.0,
                "errors": 0,
            }
        },
    }
    payload = {"run_id": "abc123", "by_model": aggregates["by_model"]}
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    jsonschema.validate(payload, schema)
    assert best_primary_score(aggregates) == 1.0
