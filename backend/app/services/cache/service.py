"""
Semantic caching: avoid redundant LLM inference for similar queries.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SemanticCache:
    """Redis-backed cache with exact-match keying. For true semantic similarity
    caching, embeddings would be compared — this uses normalized query hashing
    as a practical approximation."""

    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    def _cache_key(self, query: str, model: str, context_hash: str = "") -> str:
        normalized = query.strip().lower()
        raw = f"{model}:{context_hash}:{normalized}"
        return f"cache:llm:{hashlib.sha256(raw.encode()).hexdigest()}"

    async def get(self, query: str, model: str, context_hash: str = "") -> dict[str, Any] | None:
        r = await self._get_redis()
        key = self._cache_key(query, model, context_hash)
        data = await r.get(key)
        if data:
            logger.debug("Cache hit", key=key[:32])
            return json.loads(data)
        return None

    async def set(
        self,
        query: str,
        model: str,
        response: dict[str, Any],
        context_hash: str = "",
        ttl: int | None = None,
    ) -> None:
        r = await self._get_redis()
        key = self._cache_key(query, model, context_hash)
        ttl = ttl or settings.semantic_cache_ttl
        await r.setex(key, ttl, json.dumps(response, default=str))
        logger.debug("Cache set", key=key[:32], ttl=ttl)

    async def invalidate(self, pattern: str = "cache:llm:*") -> int:
        r = await self._get_redis()
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await r.delete(*keys)
        return len(keys)

    async def health_check(self) -> bool:
        try:
            r = await self._get_redis()
            return await r.ping()
        except Exception:
            return False


semantic_cache = SemanticCache()
