"""Anthropic Claude vision adapter."""

from __future__ import annotations

import base64

from vlm_bench.adapters.base import InferenceResult
from vlm_bench.adapters.http_base import VisionHttpAdapter
from vlm_bench.image import ProcessedImage
from vlm_bench.pricing import PricingTable


class AnthropicAdapter(VisionHttpAdapter):
    def __init__(
        self,
        model_id: str,
        *,
        api_key: str | None = None,
        timeout: float = 120.0,
        pricing: PricingTable | None = None,
    ) -> None:
        super().__init__(
            model_id,
            api_key_env="ANTHROPIC_API_KEY",
            api_key=api_key,
            timeout=timeout,
            pricing=pricing,
        )

    async def complete(
        self,
        *,
        system: str,
        user: str,
        image: ProcessedImage,
    ) -> InferenceResult:
        if not self.api_key:
            return self._missing_key_result()
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
        try:
            resp, latency_ms = await self._post(
                "https://api.anthropic.com/v1/messages",
                payload,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            if resp.status_code != 200:
                return self._api_error_result(
                    provider="Anthropic",
                    status=resp.status_code,
                    body=resp.text,
                    latency_ms=latency_ms,
                )
            data = resp.json()
            content = data["content"][0]["text"]
            usage_data = data.get("usage", {})
            return self._result_from_usage(
                raw=content,
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                latency_ms=latency_ms,
            )
        except Exception as e:
            return self._exception_result(e, 0.0)
