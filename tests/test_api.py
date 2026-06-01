"""API contract tests."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = "configs/example-bench.yaml"


def _reset_db_engine() -> None:
    import vlm_bench.storage.db as db_mod

    db_mod._engine = None
    db_mod._SessionLocal = None


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    _reset_db_engine()
    db = tmp_path / "api_test.db"
    monkeypatch.setattr("vlm_bench_api.main.DB_PATH", db)
    monkeypatch.setattr("vlm_bench_api.main.ROOT", ROOT)
    from vlm_bench_api.main import app

    with TestClient(app) as client:
        yield client
    _reset_db_engine()


def test_health(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_runs(api_client):
    resp = api_client.get("/runs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_post_runs_through_completion(api_client):
    resp = api_client.post("/runs", json={"config_path": CONFIG_PATH})
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    deadline = time.time() + 30
    status = "pending"
    while time.time() < deadline:
        detail = api_client.get(f"/runs/{run_id}").json()
        status = detail["status"]
        if status in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.2)

    assert status == "completed"
    detail = api_client.get(f"/runs/{run_id}").json()
    assert detail["metrics"]
    assert detail["progress_completed"] == detail["progress_total"]

    results = api_client.get(f"/runs/{run_id}/results")
    assert results.status_code == 200
    body = results.json()
    assert "metrics" in body
    assert body["metrics"]
    assert "aggregates" in body


def test_thumbnail_jail(api_client):
    resp = api_client.get("/thumbnails/../../../etc/passwd")
    assert resp.status_code == 404

    resp = api_client.get("/thumbnails/fixtures/images/img_001.png")
    assert resp.status_code == 200


def test_config_path_jail(api_client):
    resp = api_client.post("/runs", json={"config_path": "/etc/passwd"})
    assert resp.status_code == 400


def test_validate_config(api_client):
    resp = api_client.post("/validate", json={
        "name": "test",
        "prompts": {"system": "", "user": "test"},
        "dataset": {"manifest": "fixtures/manifest.jsonl", "base_dir": "fixtures"},
        "models": ["mock:deterministic"],
        "metric": {"type": "classification", "labels_field": "expected_class"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "valid" in data
