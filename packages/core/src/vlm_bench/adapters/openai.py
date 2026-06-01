"""OpenAI vision adapter."""

from __future__ import annotations

import base64

from vlm_bench.adapters.base import InferenceResult
from vlm_bench.adapters.http_base import VisionHttpAdapter
from vlm_bench.image import ProcessedImage
from vlm_bench.pricing import PricingTable


class OpenAIAdapter(VisionHttpAdapter):
    def __init__(
        self,
        model_id: str,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 120.0,
        pricing: PricingTable | None = None,
    ) -> None:
        super().__init__(
            model_id,
            api_key_env="OPENAI_API_KEY",
            base_url=base_url,
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
        try:
            resp, latency_ms = await self._post_json("/chat/completions", payload)
            if resp.status_code != 200:
                return self._api_error_result(
                    provider="OpenAI",
                    status=resp.status_code,
                    body=resp.text,
                    latency_ms=latency_ms,
                )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage_data = data.get("usage", {})
            return self._result_from_usage(
                raw=content,
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
                latency_ms=latency_ms,
            )
        except Exception as e:
            return self._exception_result(e, 0.0)
