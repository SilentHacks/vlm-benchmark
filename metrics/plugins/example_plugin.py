"""Example custom metric plugin."""

from vlm_bench.metrics.base import ImageContext, MetricScore


def score(ctx: ImageContext, response: str, ground_truth=None) -> MetricScore:
    """Score based on response length (demo only)."""
    length = len(response.strip())
    passed = length > 5
    score_val = min(1.0, length / 50.0)
    return MetricScore(
        score=score_val,
        passed=passed,
        details={"length": length},
    )
