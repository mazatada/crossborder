import types

from app.classify.cache import InMemoryCache
import app.classify.cache as cache_module


def test_inmemory_cache_lru_eviction():
    cache = InMemoryCache(max_size=2)
    cache.set("a", {"v": 1})
    cache.set("b", {"v": 2})
    # Access a to make it most recently used.
    assert cache.get("a") == {"v": 1}
    # Insert c -> should evict b (least recently used).
    cache.set("c", {"v": 3})
    assert cache.get("b") is None
    assert cache.get("a") == {"v": 1}
    assert cache.get("c") == {"v": 3}


def test_inmemory_cache_ttl_expiry(monkeypatch):
    cache = InMemoryCache(max_size=2)
    fake_time = types.SimpleNamespace(now=100.0)

    def _fake_time():
        return fake_time.now

    monkeypatch.setattr(cache_module.time, "time", _fake_time)

    cache.set("k", {"v": 1}, ttl=10)
    assert cache.get("k") == {"v": 1}

    fake_time.now = 111.0
    assert cache.get("k") is None
    assert "k" not in cache.cache
    assert "k" not in cache.expiry
