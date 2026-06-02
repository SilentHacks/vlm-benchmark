"""Tests for calibration and efficiency aggregates."""

from __future__ import annotations

from vlm_bench.reliability import (
    calibration_bins,
    compute_efficiency,
    compute_reliability,
    enrich_model_aggregates,
    expected_calibration_error,
    selective_prediction_curve,
)


def _row(confidence: float | None, passed: bool, cost: float = 0.01, latency: float = 100.0):
    return {
        "confidence": confidence,
        "passed": passed,
        "cost_usd": cost,
        "latency_ms": latency,
    }


def test_well_calibrated_low_ece():
    rows = [_row(0.9, True), _row(0.9, True), _row(0.1, False), _row(0.1, False)]
    bins = calibration_bins(rows, num_bins=5)
    ece = expected_calibration_error(bins, len(rows))
    assert ece is not None
    assert ece <= 0.1


def test_overconfident_bins_show_gap():
    rows = [_row(0.95, False), _row(0.95, False), _row(0.95, True)]
    rel = compute_reliability(rows, num_bins=5)
    assert rel["confidence_count"] == 3
    assert rel["ece"] is not None
    assert rel["ece"] > 0.2
    assert rel["bins"][0]["gap"] > 0.2


def test_selective_prediction_coverage_decreases():
    rows = [
        _row(0.99, True),
        _row(0.8, True),
        _row(0.6, False),
        _row(0.4, False),
    ]
    curve = selective_prediction_curve(rows, thresholds=[0.0, 0.5, 0.7, 0.9])
    assert curve[0]["coverage"] == 1.0
    assert curve[-1]["coverage"] < curve[0]["coverage"]
    assert curve[-1]["accuracy"] == 1.0


def test_compute_efficiency_cost_per_correct():
    stats = {
        "correct": 2,
        "total": 4,
        "primary_score": 0.5,
        "cost_usd": 0.04,
        "latency_ms": {"p50": 200.0, "p95": 400.0, "mean": 250.0},
    }
    eff = compute_efficiency(stats)
    assert eff["cost_per_correct_usd"] == 0.02
    assert eff["cost_per_inference_usd"] == 0.01
    assert eff["score_per_usd"] == 12.5
    assert eff["throughput_p50_ips"] == 5.0


def test_enrich_model_aggregates():
    aggregates = {
        "mock:deterministic": {
            "primary_score": 1.0,
            "correct": 2,
            "total": 2,
            "cost_usd": 0.02,
            "latency_ms": {"p50": 10.0, "p95": 12.0, "mean": 10.0},
            "errors": 0,
        }
    }
    rows_by_model = {
        "mock:deterministic": [
            _row(0.95, True, 0.01, 10.0),
            _row(0.95, True, 0.01, 10.0),
        ]
    }
    out = enrich_model_aggregates(aggregates, rows_by_model)
    assert "reliability" in out["mock:deterministic"]
    assert "efficiency" in out["mock:deterministic"]
    assert out["mock:deterministic"]["reliability"]["ece"] is not None
    assert out["mock:deterministic"]["efficiency"]["cost_per_correct_usd"] == 0.01


def test_reliability_without_confidence():
    rel = compute_reliability([_row(None, True), _row(None, False)])
    assert rel["confidence_count"] == 0
    assert rel["ece"] is None
    assert rel["bins"] == []
    assert rel["note"] is not None
