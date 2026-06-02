"""Benchmark configuration models loaded from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class PromptConfig(BaseModel):
    system: str = ""
    user: str = ""


class DatasetConfig(BaseModel):
    manifest: str
    base_dir: str | None = None


class MetricParseConfig(BaseModel):
    mode: Literal["json", "regex", "raw"] = "raw"
    path: str | None = None
    pattern: str | None = None
    group: int = 1


class MetricFieldConfig(BaseModel):
    name: str
    expected: str | None = None


# Alias used by tests
ParseConfig = MetricParseConfig


class MetricConfidenceConfig(BaseModel):
    """Optional model-reported confidence for calibration and selective prediction."""

    mode: Literal["json"] = "json"
    path: str = "$.confidence"
    scale: Literal["unit", "percent"] = "unit"


class MetricConfig(BaseModel):
    type: str
    parse: MetricParseConfig | None = None
    confidence: MetricConfidenceConfig | None = None
    labels_field: str | None = None
    aggregate: str = "accuracy"
    fields: list[MetricFieldConfig | dict[str, Any]] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    match_mode: Literal["all", "any"] = "all"
    pattern: str | None = None
    validation_schema: dict[str, Any] | None = Field(None, alias="schema")
    plugin: str | None = None


class ExecutionConfig(BaseModel):
    max_concurrency: int = 8
    cache: bool = True
    cache_ttl_hours: int | None = None
    retries: int = 2
    timeout_seconds: float = 120.0


class ImageConfig(BaseModel):
    max_long_edge: int = 1024
    jpeg_quality: int = 85


class BenchmarkConfig(BaseModel):
    name: str
    prompts: PromptConfig
    dataset: DatasetConfig
    models: list[str]
    metric: MetricConfig
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    fail_under: float | None = None

    def resolved_models(self) -> list[str]:
        return list(self.models)

    @classmethod
    def from_yaml(cls, path: str | Path) -> BenchmarkConfig:
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    def resolve_manifest_path(self, config_path: Path | None = None) -> Path:
        manifest = Path(self.dataset.manifest)
        if manifest.is_absolute():
            return manifest
        if config_path:
            for base in (config_path.parent, config_path.parent.parent, Path.cwd()):
                candidate = (base / manifest).resolve()
                if candidate.exists():
                    return candidate
            return (config_path.parent / manifest).resolve()
        return manifest.resolve()

    def resolve_base_dir(self, config_path: Path | None = None) -> Path:
        if self.dataset.base_dir:
            base = Path(self.dataset.base_dir)
            if base.is_absolute():
                return base
            if config_path:
                for root in (config_path.parent, config_path.parent.parent, Path.cwd()):
                    candidate = (root / base).resolve()
                    if candidate.exists():
                        return candidate
                return (config_path.parent / base).resolve()
            return base.resolve()
        manifest = self.resolve_manifest_path(config_path)
        return manifest.parent


class ManifestRow(BaseModel):
    image_id: str
    path: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    def get_label(self, field: str) -> Any:
        if field in self.model_dump():
            return getattr(self, field, None)
        if field in self.metadata:
            return self.metadata[field]
        extra = self.model_dump(exclude={"image_id", "path", "metadata"})
        return extra.get(field)


def load_config(path: str | Path) -> BenchmarkConfig:
    """Load benchmark config from YAML file."""
    return BenchmarkConfig.from_yaml(path)

