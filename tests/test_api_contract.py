"""Contract tests for dashboard API routes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    import vlm_bench.storage.db as db_mod

    db_mod._engines.clear()
    db_mod._sessionmakers.clear()
    db = tmp_path / "contract.db"
    monkeypatch.setattr("vlm_bench_api.main.DB_PATH", db)
    monkeypatch.setattr("vlm_bench_api.main.ROOT", ROOT)
    from vlm_bench_api.main import app

    with TestClient(app) as client:
        yield client
    db_mod._engines.clear()
    db_mod._sessionmakers.clear()


def test_contract_routes_exist(api_client):
    assert api_client.get("/health").status_code == 200
    assert api_client.get("/runs").status_code == 200
    assert (
        api_client.post(
            "/validate",
            json={
                "name": "x",
                "prompts": {"system": "", "user": "test"},
                "dataset": {"manifest": "fixtures/manifest.jsonl", "base_dir": "fixtures"},
                "models": ["mock:deterministic"],
                "metric": {"type": "classification", "labels_field": "expected_class"},
            },
        ).status_code
        == 200
    )

    run = api_client.post("/runs", json={"config_path": "configs/example-bench.yaml"})
    assert run.status_code == 200
    run_id = run.json()["run_id"]

    detail = api_client.get(f"/runs/{run_id}")
    assert detail.status_code == 200
    body = detail.json()
    for key in ("id", "status", "progress_completed", "progress_total", "aggregates"):
        assert key in body

    results = api_client.get(f"/runs/{run_id}/results")
    assert results.status_code == 200
    assert "metrics" in results.json()

    compare = api_client.get(
        "/runs/compare",
        params={"baseline": run_id, "candidate": run_id},
    )
    assert compare.status_code == 400

    assert api_client.get(f"/runs/{run_id}/events").status_code == 200
    assert api_client.get("/thumbnails/fixtures/images/img_001.png").status_code == 200
