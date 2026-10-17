import json
import logging
from functools import lru_cache
from typing import Any, Protocol

import redis

from football_api.settings import get_settings

log = logging.getLogger(__name__)


class Cache(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any) -> None: ...


class RedisCache:
    """JSON values with a TTL. Fails open: if Redis is down the API still answers from Postgres."""

    def __init__(self, url: str, ttl_seconds: int) -> None:
        self._client = redis.Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        try:
            raw = self._client.get(key)
        except redis.RedisError:
            log.warning("cache get failed; serving from database", exc_info=True)
            return None
        return json.loads(raw) if raw is not None else None

    def set(self, key: str, value: Any) -> None:
        try:
            self._client.set(key, json.dumps(value), ex=self._ttl)
        except redis.RedisError:
            log.warning("cache set failed", exc_info=True)


class MemoryCache:
    """In-process cache for tests."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        return self.store.get(key)

    def set(self, key: str, value: Any) -> None:
        self.store[key] = value


@lru_cache
def get_cache() -> Cache:
    s = get_settings()
    return RedisCache(s.redis_url, s.cache_ttl_seconds)
