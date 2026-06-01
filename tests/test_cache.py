"""Tests for inference cache."""

import pytest

from vlm_bench.adapters.base import InferenceResult
from vlm_bench.cache import InferenceCache, cache_key
from vlm_bench.storage.db import init_db, session_scope


def test_cache_key_stable():
    k1 = cache_key("m1", "sys", "user", b"bytes123")
    k2 = cache_key("m1", "sys", "user", b"bytes123")
    k3 = cache_key("m1", "sys", "user", b"different")
    assert k1 == k2
    assert k1 != k3


def test_cache_put_get(temp_db):
    init_db(temp_db)
    key = cache_key("mock:test", "s", "u", b"img")
    result = InferenceResult(
        model_id="mock:test",
        raw_response='{"label":"cat"}',
        input_tokens=10,
        output_tokens=5,
        latency_ms=50.0,
        cost_usd=0.0,
    )
    with session_scope(temp_db) as session:
        cache = InferenceCache(session)
        cache.put(key, result)
        session.commit()

    with session_scope(temp_db) as session:
        cache = InferenceCache(session)
        got = cache.get(key)
        assert got is not None
        assert got.raw_response == '{"label":"cat"}'
        assert got.cached is True
