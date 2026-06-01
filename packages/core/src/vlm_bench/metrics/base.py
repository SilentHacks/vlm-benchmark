"""Metric scoring types and protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from vlm_bench.config import ManifestRow, MetricConfig


@dataclass
class MetricScore:
    score: float
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoreContext:
    image_id: str
    prompt_system: str
    prompt_user: str
    response: str
    ground_truth: ManifestRow | None = None
    metric_config: MetricConfig | None = None


@runtime_checkable
class MetricScorer(Protocol):
    def score(self, ctx: ScoreContext) -> MetricScore: ...
