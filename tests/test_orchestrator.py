"""Integration tests with mock adapter."""

import json
from pathlib import Path

import pytest

from vlm_bench.config import BenchmarkConfig
from vlm_bench.orchestrator import BenchmarkOrchestrator
from vlm_bench.storage.db import init_db, session_scope
from vlm_bench.validation import validate_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "example-bench.yaml"


def test_validate_config():
    cfg = BenchmarkConfig.from_yaml(CONFIG_PATH)
    errors = validate_config(cfg, CONFIG_PATH)
    assert errors == [], f"Validation errors: {errors}"


@pytest.mark.asyncio
async def test_golden_run(tmp_path):
    db = tmp_path / "bench.db"
    init_db(db)
    cfg = BenchmarkConfig.from_yaml(CONFIG_PATH)

    with session_scope(db) as session:
        orch = BenchmarkOrchestrator(
            cfg,
            config_path=CONFIG_PATH,
            db_session=session,
            project_root=ROOT,
        )
        result = await orch.run()

    assert result["status"] == "completed"
    aggregates = result["aggregates"]
    by_model = aggregates.get("by_model", aggregates)
    assert "mock:deterministic" in by_model
    stats = by_model["mock:deterministic"]
    assert stats["total"] == 3
    assert stats["primary_score"] == 1.0


@pytest.mark.asyncio
async def test_resume_existing_run(tmp_path):
    db = tmp_path / "bench.db"
    init_db(db)
    cfg = BenchmarkConfig.from_yaml(CONFIG_PATH)

    with session_scope(db) as session:
        from vlm_bench.storage.models import Run

        run_id = "resume-test-01"
        session.add(
            Run(
                id=run_id,
                name="pending",
                status="pending",
                config_yaml="",
                progress_completed=0,
                progress_total=0,
            )
        )
        session.flush()

        orch = BenchmarkOrchestrator(
            cfg,
            config_path=CONFIG_PATH,
            db_session=session,
            project_root=ROOT,
        )
        result = await orch.run(run_id=run_id)

    assert result["status"] == "completed"
    with session_scope(db) as session:
        from vlm_bench.storage.models import Run

        runs = session.query(Run).filter_by(id=run_id).all()
        assert len(runs) == 1
        assert runs[0].status == "completed"


@pytest.mark.asyncio
async def test_mock_adapter_deterministic():
    from vlm_bench.adapters.mock import MockAdapter
    from vlm_bench.image import preprocess_image

    img_path = ROOT / "fixtures" / "images" / "img_001.png"
    processed = preprocess_image(img_path, "img_001")
    adapter = MockAdapter()

    r1 = await adapter.complete(system="", user="", image=processed)
    r2 = await adapter.complete(system="", user="", image=processed)
    assert r1.raw_response == r2.raw_response
