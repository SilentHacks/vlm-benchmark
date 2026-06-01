"""Vision model adapter protocol and shared types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from vlm_bench.image import ProcessedImage
from vlm_bench.pricing import TokenUsage


@dataclass
class InferenceResult:
    model_id: str
    raw_response: str
    parsed_response: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    error: str | None = None
    cached: bool = False
    metadata: dict = field(default_factory=dict)

    @property
    def usage(self) -> TokenUsage:
        return TokenUsage(input_tokens=self.input_tokens, output_tokens=self.output_tokens)


@runtime_checkable
class VisionModelAdapter(Protocol):
    id: str

    async def complete(
        self,
        *,
        system: str,
        user: str,
        image: ProcessedImage,
    ) -> InferenceResult: ...
