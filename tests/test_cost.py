"""Cost calculator tests."""

from vlm_bench.cost import aggregate_latency, aggregate_run_stats, percentile
from vlm_bench.pricing import PricingTable, TokenUsage


def test_percentile():
    assert percentile([1, 2, 3, 4, 5], 50) == 3.0


def test_aggregate_latency():
    stats = aggregate_latency([100, 200, 300, 400, 500])
    assert stats["p50"] == 300.0
    assert stats["mean"] == 300.0


def test_pricing_table():
    table = PricingTable.default()
    cost = table.compute_cost("openai:gpt-4o", TokenUsage(input_tokens=1000, output_tokens=500))
    assert cost > 0


def test_aggregate_run_stats():
    records = [
        {"model_id": "mock:a", "score": 1.0, "passed": True, "latency_ms": 10, "cost_usd": 0.01},
        {"model_id": "mock:a", "score": 0.0, "passed": False, "latency_ms": 20, "cost_usd": 0.01},
    ]
    stats = aggregate_run_stats(records)
    assert stats["mock:a"]["primary_score"] == 0.5
    assert stats["mock:a"]["correct"] == 1
