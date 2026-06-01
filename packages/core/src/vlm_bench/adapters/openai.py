"""OpenAI vision adapter."""

from __future__ import annotations

import base64
import os
import time

import httpx

from vlm_bench.adapters.base import InferenceResult
from vlm_bench.image import ProcessedImage
from vlm_bench.pricing import PricingTable, TokenUsage


class OpenAIAdapter:
    id: str

    def __init__(
        self,
        model_id: str,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 120.0,
        pricing: PricingTable | None = None,
    ) -> None:
        self.id = model_id
        self.model_name = model_id.split(":", 1)[-1] if ":" in model_id else model_id
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
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
                error="OPENAI_API_KEY not set",
            )
        b64 = base64.b64encode(image.bytes).decode("ascii")
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{image.mime_type};base64,{b64}"},
                        },
                    ],
                },
            ],
            "max_tokens": 1024,
        }
        start = time.perf_counter()
        try:
            resp = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            if resp.status_code != 200:
                return InferenceResult(
                    model_id=self.id,
                    raw_response="",
                    latency_ms=latency_ms,
                    error=f"OpenAI API error {resp.status_code}: {resp.text[:500]}",
                )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
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
