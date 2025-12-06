"""
HS分類結果のキャッシュモジュール

ルールバージョンや商品データのハッシュをキーとして、
分類結果をキャッシュします。
バックエンドとしてInMemoryとRedisをサポートします。
"""

from typing import Dict, Optional
from abc import ABC, abstractmethod
import json
import logging
import hashlib
import os

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """キャッシュバックエンドの抽象クラス"""

    @abstractmethod
    def get(self, key: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def set(self, key: str, value: Dict, ttl: int = None):
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

    @abstractmethod
    def clear(self):
        pass


class InMemoryCache(CacheBackend):
    """インメモリキャッシュ (開発・単一インスタンス用)"""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size
        self.hit_count = 0
        self.miss_count = 0

    def get(self, key: str) -> Optional[Dict]:
        result = self.cache.get(key)
        if result:
            self.hit_count += 1
            logger.debug(f"Cache HIT: {key}")
        else:
            self.miss_count += 1
            logger.debug(f"Cache MISS: {key}")
        return result

    def set(self, key: str, value: Dict, ttl: int = None):
        if len(self.cache) >= self.max_size:
            # LRU削除 (簡易実装: Python 3.7+のdict順序を利用して最も古いものを削除)
            try:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f"Cache eviction: {oldest_key}")
            except StopIteration:
                pass

        self.cache[key] = value
        logger.debug(f"Cache SET: {key}")

    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]

    def clear(self):
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0

    def get_stats(self) -> Dict:
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": round(hit_rate, 3),
            "size": len(self.cache),
            "max_size": self.max_size,
        }


class RedisCache(CacheBackend):
    """Redisキャッシュ (本番・スケールアウト用)"""

    def __init__(self, redis_client, ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = ttl

    def get(self, key: str) -> Optional[Dict]:
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None

    def set(self, key: str, value: Dict, ttl: int = None):
        ttl = ttl or self.default_ttl
        try:
            self.redis.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, key: str):
        try:
            self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    def clear(self):
        # 注意: 全キー削除は危険なので、プレフィックス付きキーのみ削除
        # ここではscan_iterを使用する実装例
        try:
            for key in self.redis.scan_iter("hs_classify:*"):
                self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")


class HSCache:
    """HSキャッシュマネージャー"""

    def __init__(self, backend: Optional[CacheBackend] = None):
        if backend:
            self.backend = backend
        else:
            # デフォルトはRedisがあればRedis、なければInMemory
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            try:
                import redis

                r = redis.from_url(redis_url)
                r.ping()  # 切断確認
                logger.info("Using Redis cache backend")
                self.backend = RedisCache(r)
            except Exception as e:
                logger.warning(
                    f"Failed to connect to Redis ({e}), falling back to InMemoryCache"
                )
                self.backend = InMemoryCache()

    def generate_cache_key(self, product_data: Dict, rules_version: str) -> str:
        """キャッシュキーを生成 (ルールバージョン含む)"""
        # 正規化
        ingredients = product_data.get("ingredients", [])
        # 成分は最大10個まで (キー肥大化防止)
        limited_ingredients = sorted(
            [ing.get("id") for ing in ingredients[:10] if isinstance(ing, dict)],
            key=str,
        )

        normalized = {
            "name": product_data.get("name", "").lower().strip()[:100],  # 100文字まで
            "category": product_data.get("category", "").lower(),
            "origin": (
                product_data.get("origin_country", "").upper()
                if product_data.get("origin_country")
                else ""
            ),
            "ingredients": limited_ingredients,
            "process": sorted(
                [str(p).lower() for p in product_data.get("process", [])[:5]]
            ),  # 5個まで
            "rules_version": rules_version,  # ルールバージョンを含める
        }

        # ハッシュ化
        key_str = json.dumps(normalized, sort_keys=True)
        return f"hs_classify:{hashlib.sha256(key_str.encode()).hexdigest()}"

    def get(self, cache_key: str) -> Optional[Dict]:
        return self.backend.get(cache_key)

    def set(self, cache_key: str, result: Dict, ttl: int = 3600):
        self.backend.set(cache_key, result, ttl)

    def invalidate_by_rules_version(self, rules_version: str):
        """ルールバージョン変更時にキャッシュを無効化"""
        logger.info(f"Invalidating cache for rules version: {rules_version}")
        self.backend.clear()
