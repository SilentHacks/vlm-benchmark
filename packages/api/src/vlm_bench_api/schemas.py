"""Pydantic request/response models for OpenAPI."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from vlm_bench.config import BenchmarkConfig


class ValidateRequest(BenchmarkConfig):
    pass


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    id: str
    project_id: str | None = None
    name: str
    status: str
    progress_completed: int
    progress_total: int
    aggregates: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    finished_at: str | None = None


class RunDetail(RunSummary):
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    inferences: list[dict[str, Any]] = Field(default_factory=list)


class RunResults(BaseModel):
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    aggregates: dict[str, Any] = Field(default_factory=dict)


class RunRef(BaseModel):
    run_id: str
    name: str
    status: str
    created_at: str | None = None
    finished_at: str | None = None


class CompareModelSummary(BaseModel):
    model_id: str
    baseline_score: float
    candidate_score: float
    score_delta: float
    baseline_cost: float
    candidate_cost: float
    cost_delta: float
    baseline_errors: int
    candidate_errors: int
    improvements: int
    regressions: int
    unchanged: int


class CompareRow(BaseModel):
    image_id: str
    model_id: str
    image_path: str
    baseline: dict[str, Any] | None = None
    candidate: dict[str, Any] | None = None
    change: str


class CompareCounts(BaseModel):
    improved: int
    regressed: int
    unchanged: int
    baseline_only: int
    candidate_only: int


class RunCompareResponse(BaseModel):
    baseline: RunRef
    candidate: RunRef
    warnings: list[str] = Field(default_factory=list)
    summary_by_model: list[CompareModelSummary] = Field(default_factory=list)
    rows: list[CompareRow] = Field(default_factory=list)
    counts: CompareCounts
