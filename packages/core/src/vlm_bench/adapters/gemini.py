"""Google Gemini vision adapter."""

from __future__ import annotations

import base64

from vlm_bench.adapters.base import InferenceResult
from vlm_bench.adapters.http_base import VisionHttpAdapter
from vlm_bench.image import ProcessedImage
from vlm_bench.pricing import PricingTable


class GeminiAdapter(VisionHttpAdapter):
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
            api_key_env="GOOGLE_API_KEY",
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
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system}]} if system else None,
            "contents": [
                {
                    "parts": [
                        {"text": user},
                        {
                            "inlineData": {
                                "mimeType": image.mime_type,
                                "data": b64,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"maxOutputTokens": 1024},
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        try:
            resp, latency_ms = await self._post(
                url,
                payload,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
            )
            if resp.status_code != 200:
                return self._api_error_result(
                    provider="Gemini",
                    status=resp.status_code,
                    body=resp.text,
                    latency_ms=latency_ms,
                )
            data = resp.json()
            parts = data["candidates"][0]["content"]["parts"]
            content = parts[0].get("text", "")
            usage_meta = data.get("usageMetadata", {})
            return self._result_from_usage(
                raw=content,
                input_tokens=usage_meta.get("promptTokenCount", 0),
                output_tokens=usage_meta.get("candidatesTokenCount", 0),
                latency_ms=latency_ms,
            )
        except Exception as e:
            return self._exception_result(e, 0.0)
