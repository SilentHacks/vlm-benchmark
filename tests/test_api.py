"""API contract tests."""

import pytest
from fastapi.testclient import TestClient

from vlm_bench_api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_runs():
    resp = client.get("/runs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_validate_config():
    resp = client.post("/validate", json={
        "name": "test",
        "prompts": {"system": "", "user": "test"},
        "dataset": {"manifest": "fixtures/manifest.jsonl", "base_dir": "fixtures"},
        "models": ["mock:deterministic"],
        "metric": {"type": "classification", "labels_field": "expected_class"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "valid" in data
