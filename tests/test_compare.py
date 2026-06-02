"""Tests for run comparison."""

from __future__ import annotations

import json
import uuid

import pytest

from vlm_bench.compare import compare_runs
from vlm_bench.storage.db import init_db, session_scope
from vlm_bench.storage.models import MetricResult, Run


def _add_run(
    session,
    *,
    run_id: str,
    name: str = "fixture-classification-v1",
    status: str = "completed",
    aggregates: dict | None = None,
) -> Run:
    agg = aggregates or {
        "mock:deterministic": {
            "primary_score": 0.667,
            "correct": 2,
            "total": 3,
            "cost_usd": 0.001,
            "errors": 0,
            "latency_ms": {"p50": 10.0, "p95": 20.0, "mean": 12.0},
        }
    }
    run = Run(
        id=run_id,
        name=name,
        status=status,
        config_yaml="",
        progress_completed=3,
        progress_total=3,
        aggregates_json=json.dumps({"by_model": agg}),
    )
    session.add(run)
    session.flush()
    return run


def _add_metric(
    session,
    *,
    run_id: str,
    image_id: str,
    model_id: str = "mock:deterministic",
    score: float = 1.0,
    passed: bool = True,
) -> None:
    session.add(
        MetricResult(
            run_id=run_id,
            image_id=image_id,
            model_id=model_id,
            score=score,
            passed=passed,
            details_json=json.dumps({"image_path": f"fixtures/images/{image_id}.png"}),
        )
    )


def _seed_baseline_candidate(session) -> tuple[str, str]:
    baseline_id = f"base-{uuid.uuid4().hex[:8]}"
    candidate_id = f"cand-{uuid.uuid4().hex[:8]}"

    _add_run(session, run_id=baseline_id)
    _add_run(
        session,
        run_id=candidate_id,
        aggregates={
            "mock:deterministic": {
                "primary_score": 1.0,
                "correct": 3,
                "total": 3,
                "cost_usd": 0.002,
                "errors": 0,
                "latency_ms": {"p50": 15.0, "p95": 25.0, "mean": 16.0},
            }
        },
    )

    # img_001: unchanged pass
    _add_metric(session, run_id=baseline_id, image_id="img_001", passed=True, score=1.0)
    _add_metric(session, run_id=candidate_id, image_id="img_001", passed=True, score=1.0)
    # img_002: regressed (pass -> fail)
    _add_metric(session, run_id=baseline_id, image_id="img_002", passed=True, score=1.0)
    _add_metric(session, run_id=candidate_id, image_id="img_002", passed=False, score=0.0)
    # img_003: improved (fail -> pass)
    _add_metric(session, run_id=baseline_id, image_id="img_003", passed=False, score=0.0)
    _add_metric(session, run_id=candidate_id, image_id="img_003", passed=True, score=1.0)

    session.flush()
    return baseline_id, candidate_id


def test_compare_happy_path(tmp_path):
    db = tmp_path / "compare.db"
    init_db(db)
    with session_scope(db) as session:
        baseline_id, candidate_id = _seed_baseline_candidate(session)

    result = compare_runs(db, baseline_id, candidate_id)

    assert result["baseline"]["run_id"] == baseline_id
    assert result["candidate"]["run_id"] == candidate_id
    assert result["counts"]["improved"] == 1
    assert result["counts"]["regressed"] == 1
    assert result["counts"]["unchanged"] == 1
    assert len(result["rows"]) == 3

    summary = result["summary_by_model"][0]
    assert summary["model_id"] == "mock:deterministic"
    assert summary["score_delta"] == pytest.approx(1.0 - 0.667, abs=1e-4)
    assert summary["improvements"] == 1
    assert summary["regressions"] == 1
    assert summary["unchanged"] == 1


def test_compare_missing_run(tmp_path):
    db = tmp_path / "compare.db"
    init_db(db)
    with pytest.raises(KeyError, match="not found"):
        compare_runs(db, "missing-a", "missing-b")


def test_compare_incomplete_run(tmp_path):
    db = tmp_path / "compare.db"
    init_db(db)
    with session_scope(db) as session:
        baseline_id = f"base-{uuid.uuid4().hex[:8]}"
        candidate_id = f"cand-{uuid.uuid4().hex[:8]}"
        _add_run(session, run_id=baseline_id, status="completed")
        _add_run(session, run_id=candidate_id, status="running")

    with pytest.raises(ValueError, match="Candidate run not completed"):
        compare_runs(db, baseline_id, candidate_id)


def test_compare_same_run_rejected(tmp_path):
    db = tmp_path / "compare.db"
    init_db(db)
    with session_scope(db) as session:
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        _add_run(session, run_id=run_id)

    with pytest.raises(ValueError, match="different runs"):
        compare_runs(db, run_id, run_id)


def test_compare_strict_name_mismatch(tmp_path):
    db = tmp_path / "compare.db"
    init_db(db)
    with session_scope(db) as session:
        baseline_id = f"base-{uuid.uuid4().hex[:8]}"
        candidate_id = f"cand-{uuid.uuid4().hex[:8]}"
        _add_run(session, run_id=baseline_id, name="bench-a")
        _add_run(session, run_id=candidate_id, name="bench-b")

    with pytest.raises(ValueError, match="Benchmark names differ"):
        compare_runs(db, baseline_id, candidate_id, strict_name=True)


def test_compare_loose_name_mismatch(tmp_path):
    db = tmp_path / "compare.db"
    init_db(db)
    with session_scope(db) as session:
        baseline_id = f"base-{uuid.uuid4().hex[:8]}"
        candidate_id = f"cand-{uuid.uuid4().hex[:8]}"
        _add_run(session, run_id=baseline_id, name="bench-a")
        _add_run(session, run_id=candidate_id, name="bench-b")
        _add_metric(session, run_id=baseline_id, image_id="img_001")
        _add_metric(session, run_id=candidate_id, image_id="img_001")

    result = compare_runs(db, baseline_id, candidate_id, strict_name=False)
    assert len(result["warnings"]) == 1
    assert "Benchmark names differ" in result["warnings"][0]


def test_compare_partial_model_overlap(tmp_path):
    db = tmp_path / "compare.db"
    init_db(db)
    with session_scope(db) as session:
        baseline_id = f"base-{uuid.uuid4().hex[:8]}"
        candidate_id = f"cand-{uuid.uuid4().hex[:8]}"
        _add_run(
            session,
            run_id=baseline_id,
            aggregates={
                "mock:deterministic": {"primary_score": 1.0, "correct": 1, "total": 1, "cost_usd": 0.0, "errors": 0},
                "openai:gpt-4o": {"primary_score": 0.5, "correct": 0, "total": 1, "cost_usd": 0.01, "errors": 0},
            },
        )
        _add_run(
            session,
            run_id=candidate_id,
            aggregates={
                "mock:deterministic": {"primary_score": 1.0, "correct": 1, "total": 1, "cost_usd": 0.0, "errors": 0},
                "anthropic:claude": {"primary_score": 0.8, "correct": 1, "total": 1, "cost_usd": 0.02, "errors": 0},
            },
        )
        _add_metric(session, run_id=baseline_id, image_id="img_001", model_id="mock:deterministic")
        _add_metric(session, run_id=candidate_id, image_id="img_001", model_id="mock:deterministic")
        _add_metric(session, run_id=baseline_id, image_id="img_001", model_id="openai:gpt-4o", passed=False, score=0.0)
        _add_metric(
            session,
            run_id=candidate_id,
            image_id="img_001",
            model_id="anthropic:claude",
            passed=True,
            score=1.0,
        )

    result = compare_runs(db, baseline_id, candidate_id)
    assert result["counts"]["baseline_only"] == 1
    assert result["counts"]["candidate_only"] == 1
    assert result["counts"]["unchanged"] == 1
    assert len(result["summary_by_model"]) == 3
