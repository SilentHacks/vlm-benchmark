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
        base_url: str = "",
        api_key: str | None = None,
        timeout: float = 120.0,
        pricing: PricingTable | None = None,
    ) -> None:
        self.id = model_id
        self.model_name = model_id.split(":", 1)[-1] if ":" in model_id else model_id
        self.api_key_env = api_key_env
        self.api_key = api_key or os.environ.get(api_key_env, "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.pricing = pricing or PricingTable.default()
        self._client = httpx.AsyncClient(timeout=timeout)

    def _missing_key_result(self) -> InferenceResult:
        return InferenceResult(
            model_id=self.id,
            raw_response="",
            error=f"{self.api_key_env} not set",
        )

    async def _post(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> tuple[httpx.Response, float]:
        start = time.perf_counter()
        resp = await self._client.post(url, headers=headers or {}, json=payload)
        return resp, self._elapsed_ms(start)

    async def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> tuple[httpx.Response, float]:
        return await self._post(
            f"{self.base_url}{path}",
            payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def _result_from_usage(
        self,
        *,
        raw: str,
        parsed: str | None = None,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        error: str | None = None,
    ) -> InferenceResult:
        cost = 0.0
        if not error:
            usage = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
            cost = self.pricing.compute_cost(self.id, usage)
        return InferenceResult(
            model_id=self.id,
            raw_response=raw,
            parsed_response=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
            error=error,
        )

    def _api_error_result(
        self, *, provider: str, status: int, body: str, latency_ms: float
    ) -> InferenceResult:
        return InferenceResult(
            model_id=self.id,
            raw_response="",
            latency_ms=latency_ms,
            error=f"{provider} API error {status}: {body[:500]}",
        )

    def _exception_result(self, exc: Exception, latency_ms: float) -> InferenceResult:
        return InferenceResult(
            model_id=self.id,
            raw_response="",
            latency_ms=latency_ms,
            error=str(exc),
        )

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return (time.perf_counter() - start) * 1000.0
