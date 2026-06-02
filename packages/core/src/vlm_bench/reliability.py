"""Calibration, selective prediction, and cost/latency efficiency aggregates."""

from __future__ import annotations

from typing import Any


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def calibration_bins(
    rows: list[dict[str, Any]],
    *,
    num_bins: int = 10,
) -> list[dict[str, Any]]:
    """Bin rows with confidence into mean confidence vs empirical accuracy."""
    scored = [r for r in rows if r.get("confidence") is not None]
    if not scored:
        return []

    bins: list[dict[str, Any]] = []
    width = 1.0 / num_bins
    for i in range(num_bins):
        low = i * width
        high = 1.0 if i == num_bins - 1 else (i + 1) * width
        in_bin = [
            r
            for r in scored
            if low <= float(r["confidence"]) < high
            or (i == num_bins - 1 and float(r["confidence"]) == 1.0)
        ]
        if not in_bin:
            continue
        confidences = [float(r["confidence"]) for r in in_bin]
        mean_conf = sum(confidences) / len(confidences)
        accuracy = sum(1 for r in in_bin if r.get("passed")) / len(in_bin)
        bins.append(
            {
                "bin_low": round(low, 4),
                "bin_high": round(high, 4),
                "count": len(in_bin),
                "mean_confidence": round(mean_conf, 4),
                "accuracy": round(accuracy, 4),
                "gap": round(abs(mean_conf - accuracy), 4),
            }
        )
    return bins


def expected_calibration_error(bins: list[dict[str, Any]], total_with_confidence: int) -> float | None:
    if not bins or total_with_confidence < 2:
        return None
    ece = 0.0
    for b in bins:
        weight = b["count"] / total_with_confidence
        ece += weight * abs(b["mean_confidence"] - b["accuracy"])
    return round(ece, 4)


def max_calibration_error(bins: list[dict[str, Any]]) -> float | None:
    if not bins:
        return None
    return round(max(b["gap"] for b in bins), 4)


def selective_prediction_curve(
    rows: list[dict[str, Any]],
    *,
    thresholds: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Accuracy and cost/latency at each minimum-confidence threshold."""
    scored = [r for r in rows if r.get("confidence") is not None]
    if not scored:
        return []

    if thresholds is None:
        thresholds = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]

    total = len(scored)
    curve: list[dict[str, Any]] = []
    for tau in thresholds:
        approved = [r for r in scored if float(r["confidence"]) >= tau]
        if not approved:
            curve.append(
                {
                    "threshold": tau,
                    "coverage": 0.0,
                    "accuracy": None,
                    "mean_cost_usd": None,
                    "mean_latency_ms": None,
                    "approved_count": 0,
                }
            )
            continue
        accuracy = sum(1 for r in approved if r.get("passed")) / len(approved)
        costs = [float(r.get("cost_usd") or 0.0) for r in approved]
        latencies = [float(r.get("latency_ms") or 0.0) for r in approved]
        curve.append(
            {
                "threshold": tau,
                "coverage": round(len(approved) / total, 4),
                "accuracy": round(accuracy, 4),
                "mean_cost_usd": round(sum(costs) / len(costs), 6),
                "mean_latency_ms": round(sum(latencies) / len(latencies), 2),
                "approved_count": len(approved),
            }
        )
    return curve


def compute_reliability(rows: list[dict[str, Any]], *, num_bins: int = 10) -> dict[str, Any]:
    """Per-model reliability summary from per-inference rows."""
    total = len(rows)
    with_confidence = [r for r in rows if r.get("confidence") is not None]
    count = len(with_confidence)
    bins = calibration_bins(with_confidence, num_bins=num_bins)
    ece = expected_calibration_error(bins, count)
    mce = max_calibration_error(bins)
    selective = selective_prediction_curve(with_confidence)

    return {
        "sample_count": total,
        "confidence_count": count,
        "confidence_available": count > 0,
        "ece": ece,
        "mce": mce,
        "bins": bins,
        "selective": selective,
        "note": None
        if count >= 2
        else (
            "Need at least 2 samples with confidence for ECE; "
            "enable metric.confidence in config and ensure models return it."
            if count == 0
            else "ECE requires at least 2 confidence samples."
        ),
    }


def compute_efficiency(model_stats: dict[str, Any]) -> dict[str, Any]:
    """Cost and throughput efficiency derived from run aggregates."""
    correct = int(model_stats.get("correct") or 0)
    total = int(model_stats.get("total") or 0)
    cost = float(model_stats.get("cost_usd") or 0.0)
    score = float(model_stats.get("primary_score") or 0.0)
    latency = model_stats.get("latency_ms") or {}
    p50 = float(latency.get("p50") or 0.0)

    cost_per_correct = round(cost / correct, 6) if correct > 0 else None
    cost_per_inference = round(cost / total, 6) if total > 0 else None
    score_per_usd = round(score / cost, 4) if cost > 0 else None
    throughput_p50_ips = round(1000.0 / p50, 4) if p50 > 0 else None

    return {
        "cost_per_correct_usd": cost_per_correct,
        "cost_per_inference_usd": cost_per_inference,
        "score_per_usd": score_per_usd,
        "throughput_p50_ips": throughput_p50_ips,
        "latency_ms_per_correct_p50": p50 if correct > 0 else None,
    }


def enrich_model_aggregates(
    aggregates: dict[str, dict[str, Any]],
    rows_by_model: dict[str, list[dict[str, Any]]],
    *,
    num_bins: int = 10,
) -> dict[str, dict[str, Any]]:
    """Attach reliability and efficiency blocks to each model in aggregates."""
    enriched: dict[str, dict[str, Any]] = {}
    for model_id, stats in aggregates.items():
        merged = dict(stats)
        model_rows = rows_by_model.get(model_id, [])
        merged["reliability"] = compute_reliability(model_rows, num_bins=num_bins)
        merged["efficiency"] = compute_efficiency(merged)
        enriched[model_id] = merged
    return enriched
