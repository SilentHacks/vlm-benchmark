"""Metric scoring types, helpers, and protocol."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from jsonpath_ng import parse as jsonpath_parse

from vlm_bench.config import ManifestRow, MetricConfig, MetricParseConfig


@dataclass
class MetricScore:
    score: float
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageContext:
    image_id: str
    manifest_row: dict[str, Any]

    @classmethod
    def from_row(cls, row: ManifestRow) -> ImageContext:
        return cls(image_id=row.image_id, manifest_row=row.model_dump())


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
    def score(
        self, ctx: ImageContext, response: str, ground_truth: Any | None = None
    ) -> MetricScore: ...


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    return str(value).strip().lower()


def parse_response(response: str, parse_cfg: MetricParseConfig | None) -> Any:
    if parse_cfg is None or parse_cfg.mode == "raw":
        return response.strip()

    if parse_cfg.mode == "json":
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
            if match:
                data = json.loads(match.group(1))
            else:
                match = re.search(r"\{[\s\S]*\}", response)
                if match:
                    data = json.loads(match.group(0))
                else:
                    return response.strip()
        if parse_cfg.path:
            matches = jsonpath_parse(parse_cfg.path).find(data)
            return matches[0].value if matches else None
        return data

    if parse_cfg.mode == "regex" and parse_cfg.pattern:
        match = re.search(parse_cfg.pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(parse_cfg.group)
        return None

    return response.strip()


def score_response(
    config: MetricConfig,
    ctx: ImageContext,
    response: str,
    *,
    plugins_dir: str | None = None,
) -> MetricScore:
    from vlm_bench.metrics.builtin import get_scorer

    labels_field = config.labels_field or "expected_class"
    ground_truth = ctx.manifest_row.get(labels_field)
    scorer = get_scorer(config, plugins_dir)
    return scorer.score(ctx, response, ground_truth)
