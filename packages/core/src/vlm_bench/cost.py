"""Cost aggregation and latency statistics."""

from __future__ import annotations

from typing import Any


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


def aggregate_latency(latencies: list[float]) -> dict[str, float]:
    return {
        "p50": percentile(latencies, 50),
        "p95": percentile(latencies, 95),
        "mean": sum(latencies) / len(latencies) if latencies else 0.0,
    }


def aggregate_run_stats(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_model: dict[str, list[dict]] = {}
    for r in records:
        mid = r.get("model_id", "unknown")
        by_model.setdefault(mid, []).append(r)

    result: dict[str, dict[str, Any]] = {}
    for model_id, rows in by_model.items():
        scores = [r["score"] for r in rows if r.get("score") is not None]
        latencies = [r["latency_ms"] for r in rows if r.get("latency_ms") is not None]
        costs = [r.get("cost_usd", 0.0) or 0.0 for r in rows]
        errors = sum(1 for r in rows if r.get("error"))
        passed = sum(1 for r in rows if r.get("passed"))
        result[model_id] = {
            "primary_score": sum(scores) / len(scores) if scores else 0.0,
            "correct": passed,
            "total": len(rows),
            "latency_ms": aggregate_latency(latencies),
            "cost_usd": round(sum(costs), 4),
            "errors": errors,
        }
    return result
