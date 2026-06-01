"""API response serializers."""

from __future__ import annotations

import json

from vlm_bench.storage.models import InferenceRecord, MetricResult, Run


def run_to_dict(run: Run) -> dict:
    raw = json.loads(run.aggregates_json or "{}")
    by_model = raw.get("by_model", raw)
    return {
        "id": run.id,
        "project_id": run.project_id,
        "name": run.name,
        "status": run.status,
        "progress_completed": run.progress_completed,
        "progress_total": run.progress_total,
        "aggregates": {"by_model": by_model},
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


def metric_to_dict(m: MetricResult) -> dict:
    details = json.loads(m.details_json or "{}")
    image_path = details.pop("image_path", None) or f"fixtures/images/{m.image_id}.png"
    return {
        "image_id": m.image_id,
        "model_id": m.model_id,
        "score": m.score,
        "passed": m.passed,
        "image_path": image_path,
        "details": details,
    }


def inf_to_dict(i: InferenceRecord) -> dict:
    return {
        "image_id": i.image_id,
        "model_id": i.model_id,
        "raw_response": i.raw_response,
        "latency_ms": i.latency_ms,
        "cost_usd": i.cost_usd,
        "error": i.error,
        "cached": i.cached,
    }


def run_results_payload(run: Run, metrics: list[MetricResult]) -> dict:
    raw = json.loads(run.aggregates_json or "{}")
    by_model = raw.get("by_model", raw)
    return {
        "metrics": [metric_to_dict(m) for m in metrics],
        "aggregates": {"by_model": by_model},
    }


def run_detail_payload(
    run: Run,
    metrics: list[MetricResult],
    inferences: list[InferenceRecord],
) -> dict:
    return {
        **run_to_dict(run),
        "metrics": [metric_to_dict(m) for m in metrics],
        "inferences": [inf_to_dict(i) for i in inferences],
    }
