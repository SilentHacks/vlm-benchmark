"""Deterministic mock adapter for testing without live APIs."""

from __future__ import annotations

import asyncio
import hashlib
import json

from vlm_bench.adapters.base import InferenceResult
from vlm_bench.image import ProcessedImage


class MockAdapter:
    """Returns deterministic JSON responses based on image hash."""

    def __init__(self, model_id: str = "mock:deterministic", latency_ms: float = 5.0) -> None:
        self.id = model_id
        self.latency_ms = latency_ms

    async def complete(
        self,
        *,
        system: str,
        user: str,
        image: ProcessedImage,
    ) -> InferenceResult:
        await asyncio.sleep(self.latency_ms / 1000.0)
        label_map = {"img_001": "defect", "img_002": "ok", "img_003": "defect"}
        if image.image_id in label_map:
            label = label_map[image.image_id]
        else:
            img_hash = hashlib.sha256(image.bytes).hexdigest()
            labels = ["defect", "ok", "defect"]
            label = labels[int(img_hash[:8], 16) % len(labels)]
        response = json.dumps({"label": label, "confidence": 0.95})
        return InferenceResult(
            model_id=self.id,
            raw_response=response,
            parsed_response=response,
            input_tokens=100,
            output_tokens=20,
            latency_ms=self.latency_ms,
            cost_usd=0.0,
        )
