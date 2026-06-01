"""Tests for pricing and cost tracking."""

from pathlib import Path

from vlm_bench.pricing import CostLatencyTracker, PricingTable, TokenUsage

ROOT = Path(__file__).resolve().parents[1]


def test_pricing_compute_cost():
    pricing = PricingTable.default()
    usage = TokenUsage(input_tokens=1000, output_tokens=500)
    cost = pricing.compute_cost("openai:gpt-4o", usage)
    assert cost == 2.5 + 5.0  # 1k input @ 2.5 + 0.5k output @ 10


def test_pricing_yaml_per_million_keys():
    table = PricingTable.from_yaml(ROOT / "configs" / "pricing.yaml")
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
    yaml_cost = table.compute_cost("openai:gpt-4o", usage)
    default_cost = PricingTable.default().compute_cost("openai:gpt-4o", usage)
    assert yaml_cost == 2.5 + 10.0
    assert default_cost == 12500.0
    assert yaml_cost != default_cost


def test_cost_tracker_summary():
    pricing = PricingTable.default()
    tracker = CostLatencyTracker(pricing)
    tracker.record("mock:test", usage=TokenUsage(100, 20), latency_ms=100.0)
    tracker.record("mock:test", usage=TokenUsage(100, 20), latency_ms=200.0)
    summary = tracker.summary()
    assert "mock:test" in summary
    assert summary["mock:test"]["latency_ms"]["p50"] == 200.0
    assert summary["mock:test"]["latency_ms"]["mean"] == 150.0
