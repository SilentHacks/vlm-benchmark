"""Adapter factory registry."""

from __future__ import annotations

from vlm_bench.adapters.anthropic import AnthropicAdapter
from vlm_bench.adapters.base import VisionModelAdapter
from vlm_bench.adapters.gemini import GeminiAdapter
from vlm_bench.adapters.mock import MockAdapter
from vlm_bench.adapters.openai import OpenAIAdapter
from vlm_bench.pricing import PricingTable

ADAPTER_PREFIXES = ("mock:", "openai:", "google:", "gemini:", "anthropic:")


def create_adapter(
    model_id: str,
    pricing: PricingTable | None = None,
    timeout: float = 120.0,
) -> VisionModelAdapter:
    pricing = pricing or PricingTable.default()
    if model_id.startswith("mock:"):
        return MockAdapter(model_id)
    if model_id.startswith("openai:"):
        return OpenAIAdapter(model_id, pricing=pricing, timeout=timeout)
    if model_id.startswith("google:") or model_id.startswith("gemini:"):
        return GeminiAdapter(model_id, pricing=pricing, timeout=timeout)
    if model_id.startswith("anthropic:"):
        return AnthropicAdapter(model_id, pricing=pricing, timeout=timeout)
    raise ValueError(
        f"Unknown model: {model_id}. "
        "Use a known prefix: mock:, openai:, google:, gemini:, or anthropic:"
    )


def get_available_adapters() -> list[str]:
    return [
        "mock:deterministic",
        "openai:gpt-4o",
        "google:gemini-2.0-flash",
        "anthropic:claude-3-5-sonnet-20241022",
    ]
