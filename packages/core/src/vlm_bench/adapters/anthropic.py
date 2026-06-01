"""Anthropic Claude vision adapter."""

from __future__ import annotations

import base64
import os
import time

import httpx

from vlm_bench.adapters.base import InferenceResult
from vlm_bench.image import ProcessedImage
from vlm_bench.pricing import PricingTable, TokenUsage


class AnthropicAdapter:
    id: str

    def __init__(
        self,
        model_id: str,
        *,
        api_key: str | None = None,
        timeout: float = 120.0,
        pricing: PricingTable | None = None,
    ) -> None:
        self.id = model_id
        self.model_name = model_id.split(":", 1)[-1] if ":" in model_id else model_id
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.timeout = timeout
        self.pricing = pricing or PricingTable.default()
        self._client = httpx.AsyncClient(timeout=timeout)

    async def complete(
        self,
        *,
        system: str,
        user: str,
        image: ProcessedImage,
    ) -> InferenceResult:
        if not self.api_key:
            return InferenceResult(
                model_id=self.id,
                raw_response="",
                error="ANTHROPIC_API_KEY not set",
            )
        b64 = base64.b64encode(image.bytes).decode("ascii")
        payload = {
            "model": self.model_name,
            "max_tokens": 1024,
            "system": system,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image.mime_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": user},
                    ],
                }
            ],
        }
        start = time.perf_counter()
        try:
            resp = await self._client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            if resp.status_code != 200:
                return InferenceResult(
                    model_id=self.id,
                    raw_response="",
                    latency_ms=latency_ms,
                    error=f"Anthropic API error {resp.status_code}: {resp.text[:500]}",
                )
            data = resp.json()
            content = data["content"][0]["text"]
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
            )
            cost = self.pricing.compute_cost(self.id, usage)
            return InferenceResult(
                model_id=self.id,
                raw_response=content,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return InferenceResult(
                model_id=self.id,
                raw_response="",
                latency_ms=latency_ms,
                error=str(e),
            )

    async def close(self) -> None:
        await self._client.aclose()
