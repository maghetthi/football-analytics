from football_api.cache import MemoryCache, RedisCache


def test_memory_cache_roundtrip():
    c = MemoryCache()
    assert c.get("k") is None
    c.set("k", {"a": 1})
    assert c.get("k") == {"a": 1}


def test_redis_cache_fails_open_when_redis_is_down():
    # Port 1 refuses connections: the API must keep answering from Postgres.
    c = RedisCache("redis://127.0.0.1:1/0", ttl_seconds=10)
    assert c.get("k") is None
    c.set("k", {"a": 1})  # must not raise
