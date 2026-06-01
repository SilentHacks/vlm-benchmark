"""Inference cache backed by SQLite."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from vlm_bench.adapters.base import InferenceResult
from vlm_bench.storage.models import CacheEntry


def cache_key(
    model_id: str,
    system: str,
    user: str,
    image_bytes: bytes,
    generation_params: dict | None = None,
) -> str:
    params = json.dumps(generation_params or {}, sort_keys=True)
    payload = f"{model_id}|{system}|{user}|{hashlib.sha256(image_bytes).hexdigest()}|{params}"
    return hashlib.sha256(payload.encode()).hexdigest()


class InferenceCache:
    def __init__(self, session: Session, ttl_hours: int | None = None) -> None:
        self._session = session
        self._ttl_hours = ttl_hours

    def get(self, key: str) -> InferenceResult | None:
        entry = self._session.get(CacheEntry, key)
        if entry is None:
            return None
        if self._ttl_hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self._ttl_hours)
            created = entry.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created < cutoff:
                self._session.delete(entry)
                self._session.flush()
                return None
        return InferenceResult(
            model_id=entry.model_id,
            raw_response=entry.raw_response,
            parsed_response=entry.parsed_response,
            input_tokens=entry.input_tokens,
            output_tokens=entry.output_tokens,
            latency_ms=entry.latency_ms,
            cost_usd=entry.cost_usd,
            cached=True,
        )

    def put(self, key: str, result: InferenceResult) -> None:
        existing = self._session.get(CacheEntry, key)
        if existing:
            existing.raw_response = result.raw_response
            existing.parsed_response = result.parsed_response
            existing.input_tokens = result.input_tokens
            existing.output_tokens = result.output_tokens
            existing.latency_ms = result.latency_ms
            existing.cost_usd = result.cost_usd
        else:
            self._session.add(
                CacheEntry(
                    cache_key=key,
                    model_id=result.model_id,
                    raw_response=result.raw_response,
                    parsed_response=result.parsed_response,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    latency_ms=result.latency_ms,
                    cost_usd=result.cost_usd,
                )
            )
        self._session.flush()

    def clear(self) -> int:
        entries = self._session.scalars(select(CacheEntry)).all()
        count = len(entries)
        for e in entries:
            self._session.delete(e)
        self._session.flush()
        return count
