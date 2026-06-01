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
