"""Post-run validation helpers."""

from __future__ import annotations

from typing import Any

from vlm_bench.config import BenchmarkConfig


def best_primary_score(aggregates: dict[str, Any]) -> float:
    by_model = aggregates.get("by_model", aggregates)
    if not isinstance(by_model, dict):
        return 0.0
    scores = [
        float(stats.get("primary_score", 0))
        for stats in by_model.values()
        if isinstance(stats, dict)
    ]
    return max(scores) if scores else 0.0


def check_fail_under(
    config: BenchmarkConfig, aggregates: dict[str, Any]
) -> tuple[bool, float, float | None]:
    """Return (passed, best_score, threshold). passed is True when no threshold set."""
    threshold = config.fail_under
    best = best_primary_score(aggregates)
    if threshold is None:
        return True, best, None
    return best >= threshold, best, threshold
