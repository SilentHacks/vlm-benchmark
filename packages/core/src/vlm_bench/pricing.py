"""Cost and latency tracking with vendor pricing tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class PricingEntry:
    input_per_1k: float = 0.0
    output_per_1k: float = 0.0


class PricingTable:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._entries: dict[str, PricingEntry] = {}
        if data:
            for model_id, entry in data.get("models", {}).items():
                self._entries[model_id] = PricingEntry(
                    input_per_1k=float(entry.get("input_per_1k", 0)),
                    output_per_1k=float(entry.get("output_per_1k", 0)),
                )

    @classmethod
    def from_yaml(cls, path: Path) -> PricingTable:
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        models: dict[str, dict[str, float]] = {}
        for model_id, entry in raw.get("models", {}).items():
            if not isinstance(entry, dict):
                continue
            input_per_1k = entry.get("input_per_1k")
            output_per_1k = entry.get("output_per_1k")
            if input_per_1k is None and "input_per_1m" in entry:
                input_per_1k = float(entry["input_per_1m"]) / 1000.0
            if output_per_1k is None and "output_per_1m" in entry:
                output_per_1k = float(entry["output_per_1m"]) / 1000.0
            models[model_id] = {
                "input_per_1k": float(input_per_1k or 0),
                "output_per_1k": float(output_per_1k or 0),
            }
        return cls({"models": models})

    @classmethod
    def default(cls) -> PricingTable:
        return cls(
            {
                "models": {
                    "mock:deterministic": {"input_per_1k": 0.0, "output_per_1k": 0.0},
                    "openai:gpt-4o": {"input_per_1k": 2.5, "output_per_1k": 10.0},
                    "openai:gpt-4o-mini": {"input_per_1k": 0.15, "output_per_1k": 0.6},
                    "google:gemini-2.0-flash": {"input_per_1k": 0.1, "output_per_1k": 0.4},
                    "anthropic:claude-3-5-sonnet-20241022": {
                        "input_per_1k": 3.0,
                        "output_per_1k": 15.0,
                    },
                }
            }
        )

    def compute_cost(self, model_id: str, usage: TokenUsage) -> float:
        entry = self._entries.get(model_id, PricingEntry())
        return (usage.input_tokens / 1000 * entry.input_per_1k) + (
            usage.output_tokens / 1000 * entry.output_per_1k
        )


@dataclass
class LatencyStats:
    values_ms: list[float] = field(default_factory=list)

    def add(self, latency_ms: float) -> None:
        self.values_ms.append(latency_ms)

    @property
    def p50(self) -> float:
        if not self.values_ms:
            return 0.0
        sorted_vals = sorted(self.values_ms)
        idx = len(sorted_vals) // 2
        return sorted_vals[idx]

    @property
    def p95(self) -> float:
        if not self.values_ms:
            return 0.0
        sorted_vals = sorted(self.values_ms)
        idx = int(len(sorted_vals) * 0.95)
        idx = min(idx, len(sorted_vals) - 1)
        return sorted_vals[idx]

    @property
    def mean(self) -> float:
        if not self.values_ms:
            return 0.0
        return sum(self.values_ms) / len(self.values_ms)


@dataclass
class CostLatencyTracker:
    pricing: PricingTable
    cost_by_model: dict[str, float] = field(default_factory=dict)
    latency_by_model: dict[str, LatencyStats] = field(default_factory=dict)
    errors_by_model: dict[str, int] = field(default_factory=dict)

    def record(
        self,
        model_id: str,
        *,
        usage: TokenUsage | None = None,
        latency_ms: float = 0.0,
        error: bool = False,
    ) -> float:
        cost = 0.0
        if usage:
            cost = self.pricing.compute_cost(model_id, usage)
            self.cost_by_model[model_id] = self.cost_by_model.get(model_id, 0.0) + cost
        if latency_ms > 0:
            if model_id not in self.latency_by_model:
                self.latency_by_model[model_id] = LatencyStats()
            self.latency_by_model[model_id].add(latency_ms)
        if error:
            self.errors_by_model[model_id] = self.errors_by_model.get(model_id, 0) + 1
        return cost

    def summary(self) -> dict[str, Any]:
        from vlm_bench.cost import aggregate_latency

        result: dict[str, Any] = {}
        all_models = set(self.cost_by_model) | set(self.latency_by_model) | set(self.errors_by_model)
        for model_id in all_models:
            lat = self.latency_by_model.get(model_id, LatencyStats())
            result[model_id] = {
                "cost_usd": round(self.cost_by_model.get(model_id, 0.0), 6),
                "latency_ms": aggregate_latency(lat.values_ms),
                "errors": self.errors_by_model.get(model_id, 0),
            }
        return result
