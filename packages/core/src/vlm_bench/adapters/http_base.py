"""Shared HTTP client helpers for vision API adapters."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from vlm_bench.adapters.base import InferenceResult
from vlm_bench.pricing import PricingTable, TokenUsage


class VisionHttpAdapter:
    def __init__(
        self,
        model_id: str,
        *,
        api_key_env: str,
        base_url: str,
        timeout: float = 120.0,
        pricing: PricingTable | None = None,
    ) -> None:
        self.id = model_id
        self.model_name = model_id.split(":", 1)[-1] if ":" in model_id else model_id
        self.api_key = os.environ.get(api_key_env, "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.pricing = pricing or PricingTable.default()
        self._client = httpx.AsyncClient(timeout=timeout)

    async def _post_json(self, path: str, payload: dict[str, Any]) -> httpx.Response:
        return await self._client.post(
            f"{self.base_url}{path}",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    def _result_from_usage(
        self,
        *,
        raw: str,
        parsed: str | None,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        error: str | None = None,
    ) -> InferenceResult:
        usage = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
        cost = self.pricing.compute_cost(self.id, usage) if not error else 0.0
        return InferenceResult(
            model_id=self.id,
            raw_response=raw,
            parsed_response=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
            error=error,
            usage=usage,
        )

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return (time.perf_counter() - start) * 1000.0
