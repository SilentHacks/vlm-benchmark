"""Run-to-run comparison for regression analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vlm_bench.results import load_run_results
from vlm_bench.storage.models import MetricResult, Run


def _run_meta(run: Run) -> dict[str, Any]:
    return {
        "run_id": run.id,
        "name": run.name,
        "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


def _image_path(m: MetricResult) -> str:
    details = json.loads(m.details_json or "{}")
    return details.get("image_path") or f"fixtures/images/{m.image_id}.png"


def _metric_side(m: MetricResult | None) -> dict[str, Any] | None:
    if m is None:
        return None
    return {"score": m.score, "passed": m.passed}


def _classify_change(
    baseline: MetricResult | None, candidate: MetricResult | None
) -> str:
    if baseline is None and candidate is None:
        return "unchanged"
    if baseline is None:
        return "candidate_only"
    if candidate is None:
        return "baseline_only"
    if baseline.passed and not candidate.passed:
        return "regressed"
    if not baseline.passed and candidate.passed:
        return "improved"
    return "unchanged"


def compare_runs(
    db_path: Path | str,
    baseline_id: str,
    candidate_id: str,
    *,
    strict_name: bool = True,
) -> dict[str, Any]:
    """Compare two completed runs and return aggregate + per-row diffs."""
    if baseline_id == candidate_id:
        raise ValueError("baseline and candidate must be different runs")

    baseline_dto = load_run_results(db_path, baseline_id)
    candidate_dto = load_run_results(db_path, candidate_id)

    baseline_run = baseline_dto.run
    candidate_run = candidate_dto.run

    if baseline_run.status != "completed":
        raise ValueError(f"Baseline run not completed: {baseline_id} ({baseline_run.status})")
    if candidate_run.status != "completed":
        raise ValueError(f"Candidate run not completed: {candidate_id} ({candidate_run.status})")

    warnings: list[str] = []
    if baseline_run.name != candidate_run.name:
        msg = (
            f"Benchmark names differ: baseline={baseline_run.name!r}, "
            f"candidate={candidate_run.name!r}"
        )
        if strict_name:
            raise ValueError(msg)
        warnings.append(msg)

    baseline_by_key: dict[tuple[str, str], MetricResult] = {
        (m.image_id, m.model_id): m for m in baseline_dto.metrics
    }
    candidate_by_key: dict[tuple[str, str], MetricResult] = {
        (m.image_id, m.model_id): m for m in candidate_dto.metrics
    }

    all_keys = sorted(set(baseline_by_key) | set(candidate_by_key))
    rows: list[dict[str, Any]] = []
    counts = {
        "improved": 0,
        "regressed": 0,
        "unchanged": 0,
        "baseline_only": 0,
        "candidate_only": 0,
    }

    per_model_counts: dict[str, dict[str, int]] = {}

    for image_id, model_id in all_keys:
        b = baseline_by_key.get((image_id, model_id))
        c = candidate_by_key.get((image_id, model_id))
        change = _classify_change(b, c)
        counts[change] += 1

        if change in ("improved", "regressed", "unchanged"):
            mc = per_model_counts.setdefault(
                model_id,
                {"improved": 0, "regressed": 0, "unchanged": 0},
            )
            mc[change] += 1

        image_path = _image_path(b or c)  # type: ignore[arg-type]
        rows.append(
            {
                "image_id": image_id,
                "model_id": model_id,
                "image_path": image_path,
                "baseline": _metric_side(b),
                "candidate": _metric_side(c),
                "change": change,
            }
        )

    baseline_agg = baseline_dto.aggregates.get("by_model", {})
    candidate_agg = candidate_dto.aggregates.get("by_model", {})
    all_models = sorted(set(baseline_agg) | set(candidate_agg))

    summary_by_model: list[dict[str, Any]] = []
    for model_id in all_models:
        b_stats = baseline_agg.get(model_id, {})
        c_stats = candidate_agg.get(model_id, {})
        b_score = b_stats.get("primary_score", 0.0)
        c_score = c_stats.get("primary_score", 0.0)
        b_cost = b_stats.get("cost_usd", 0.0)
        c_cost = c_stats.get("cost_usd", 0.0)
        mc = per_model_counts.get(
            model_id, {"improved": 0, "regressed": 0, "unchanged": 0}
        )
        summary_by_model.append(
            {
                "model_id": model_id,
                "baseline_score": b_score,
                "candidate_score": c_score,
                "score_delta": round(c_score - b_score, 6),
                "baseline_cost": b_cost,
                "candidate_cost": c_cost,
                "cost_delta": round(c_cost - b_cost, 6),
                "baseline_errors": b_stats.get("errors", 0),
                "candidate_errors": c_stats.get("errors", 0),
                "improvements": mc["improved"],
                "regressions": mc["regressed"],
                "unchanged": mc["unchanged"],
            }
        )

    summary_by_model.sort(key=lambda x: x["score_delta"], reverse=True)

    return {
        "baseline": _run_meta(baseline_run),
        "candidate": _run_meta(candidate_run),
        "warnings": warnings,
        "summary_by_model": summary_by_model,
        "rows": rows,
        "counts": counts,
    }
