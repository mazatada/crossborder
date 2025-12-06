"""
キャッシュ機能のユニットテスト
"""

from unittest.mock import MagicMock
from app.classify.cache import HSCache, InMemoryCache
from app.classify.classifier import HSClassifier


class TestHSCache:

    def test_cache_key_generation(self):
        """キャッシュキー生成のテスト"""
        cache = HSCache(backend=InMemoryCache())

        product_data = {
            "name": "Test Product",
            "category": "confectionery",
            "ingredients": [{"id": "sugar", "pct": 50}],
            "process": ["baking"],
        }
        rules_version = "1.0.0"

        key1 = cache.generate_cache_key(product_data, rules_version)
        key2 = cache.generate_cache_key(product_data, rules_version)

        # 同じデータなら同じキー
        assert key1 == key2

        # データが変われば違うキー
        product_data_diff = product_data.copy()
        product_data_diff["name"] = "Different Product"
        key3 = cache.generate_cache_key(product_data_diff, rules_version)
        assert key1 != key3

        # ルールバージョンが変われば違うキー
        key4 = cache.generate_cache_key(product_data, "1.0.1")
        assert key1 != key4

        # 順序が変わっても同じキー (正規化の確認)
        product_data_reordered = {
            "process": ["baking"],
            "ingredients": [{"id": "sugar", "pct": 50}],
            "category": "confectionery",
            "name": "Test Product",
        }
        key5 = cache.generate_cache_key(product_data_reordered, rules_version)
        assert key1 == key5

    def test_in_memory_cache(self):
        """InMemoryキャッシュの動作テスト"""
        backend = InMemoryCache(max_size=2)
        cache = HSCache(backend=backend)

        key1 = "key1"
        val1 = {"data": "value1"}

        # SET
        cache.set(key1, val1)

        # GET
        assert cache.get(key1) == val1

        # MISS
        assert cache.get("unknown") is None

        # Eviction (LRU)
        cache.set("key2", {"data": "value2"})
        cache.set("key3", {"data": "value3"})  # ここでkey1が消えるはず

        assert cache.get(key1) is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None





class TestClassifierCache:
    """ClassifierとCacheの統合テスト"""

    def test_cache_integration(self):
        classifier = HSClassifier()
        # Mock backend to verify calls
        mock_backend = MagicMock()
        mock_backend.get.return_value = None
        classifier.cache.backend = mock_backend

        product_data = {
            "name": "Cache Test Cookie",
            "category": "confectionery",
            "ingredients": [{"id": "wheat_flour", "pct": 40}],
            "process": ["baking"],
        }

        # 1回目：キャッシュミス → 分類実行 → キャッシュセット
        result1 = classifier.classify(product_data)
        assert result1["cache_hit"] is False
        mock_backend.get.assert_called_once()
        mock_backend.set.assert_called_once()

        # キャッシュにデータが入った状態をモック
        mock_backend.get.return_value = result1
        mock_backend.get.reset_mock()
        mock_backend.set.reset_mock()

        # 2回目：キャッシュヒット
        result2 = classifier.classify(product_data)
        assert result2["cache_hit"] is True
        # 結果の中身は同じはず（cache_hitフラグ以外）
        assert result2["final_hs_code"] == result1["final_hs_code"]
        mock_backend.get.assert_called_once()
        mock_backend.set.assert_not_called()
