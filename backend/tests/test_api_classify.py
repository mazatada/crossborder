"""
HS分類API統合テスト
"""

import pytest
from app.models import HSClassification, AuditEvent


class TestClassifyHSAPI:
    """HS分類APIの統合テスト"""

    def test_classify_chocolate_cookies_success(self, client, api_key_header):
        """チョコレートクッキーの分類テスト (正常系)"""
        response = client.post(
            "/v1/classify/hs",
            json={
                "product": {
                    "name": "Chocolate cookies",
                    "category": "confectionery",
                    "origin_country": "JP",
                    "ingredients": [
                        {"id": "ing_wheat_flour", "pct": 30.0},
                        {"id": "ing_sugar", "pct": 25.0},
                        {"id": "ing_cocoa", "pct": 15.0},
                    ],
                    "process": ["baking"],
                },
                "traceId": "TEST-HS-001",
            },
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.get_json()

        # OpenAPI準拠のレスポンス検証
        assert "hs_candidates" in data
        assert "final_hs_code" in data
        assert "duty_rate" in data
        assert "risk_flags" in data
        assert "quota_applicability" in data
        assert "review_required" in data
        assert "explanations" in data
        assert "metadata" in data

        # Explanations検証
        explanations = data["explanations"]
        assert len(explanations) > 0
        exp_ids = [e["id"] for e in explanations]
        # ルールマッチ、主要成分、加工方法などの説明が含まれるはず
        assert any(e_id.startswith("rule_match_") for e_id in exp_ids)
        assert "ingredient_major_ing_wheat_flour" in exp_ids
        assert "process_match_baking" in exp_ids

        # 候補検証
        assert len(data["hs_candidates"]) > 0
        assert data["final_hs_code"] in ["1905.90", "1806.90"]

        # メタデータ検証
        assert data["metadata"]["classification_method"] == "rule_based"
        assert data["metadata"]["rules_version"] == "1.1.0"
        assert "processing_time_ms" in data["metadata"]

        # duty_rate 互換検証（移行期間）
        duty_rate = data["duty_rate"]
        assert "ad_valorem_rate" in duty_rate
        assert "ad_valorem_pct" in duty_rate
        # 移行期間中はnull許容
        assert duty_rate["ad_valorem_rate"] is None

    def test_classify_saves_to_database(self, client, api_key_header, db_session):
        """DB保存の確認"""
        response = client.post(
            "/v1/classify/hs",
            json={
                "product": {
                    "name": "Test product",
                    "category": "confectionery",
                    "ingredients": [{"id": "ing_wheat_flour", "pct": 35.0}],
                    "process": ["baking"],
                },
                "traceId": "TEST-HS-DB-001",
            },
            headers=api_key_header,
        )

        assert response.status_code == 200

        # DB確認
        classification = (
            db_session.query(HSClassification)
            .filter_by(trace_id="TEST-HS-DB-001")
            .first()
        )

        assert classification is not None
        assert classification.product_name == "Test product"
        assert classification.final_hs_code == "1905.90"
        assert classification.classification_method == "rule_based"
        assert classification.rules_version == "1.1.0"

    def test_classify_creates_audit_log(self, client, api_key_header, db_session):
        """監査ログの確認"""
        response = client.post(
            "/v1/classify/hs",
            json={
                "product": {
                    "name": "Audit test product",
                    "category": "confectionery",
                    "ingredients": [{"id": "ing_wheat_flour", "pct": 40.0}],
                    "process": ["baking"],
                },
                "traceId": "TEST-HS-AUDIT-001",
            },
            headers=api_key_header,
        )

        assert response.status_code == 200

        # 監査ログ確認
        events = (
            db_session.query(AuditEvent).filter_by(trace_id="TEST-HS-AUDIT-001").all()
        )

        assert len(events) >= 2  # requested + completed
        event_types = [e.event for e in events]
        assert "hs_classification_requested" in event_types
        assert "hs_classification_completed" in event_types

    def test_classify_missing_product(self, client, api_key_header):
        """productフィールド欠落 (400エラー)"""
        response = client.post("/v1/classify/hs", json={}, headers=api_key_header)

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["error"]["class"] == "missing_required"
        # 空のJSONの場合は"product"フィールドが欠落
        assert data["error"]["field"] in ["product", "body"]

    def test_classify_product_not_object(self, client, api_key_header):
        """productがobject以外 (400エラー)"""
        response = client.post(
            "/v1/classify/hs",
            json={"product": "invalid"},
            headers=api_key_header,
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["error"]["class"] == "invalid_argument"
        assert data["error"]["field"] == "product"

    def test_classify_missing_product_name(self, client, api_key_header):
        """product.name欠落 (400エラー)"""
        response = client.post(
            "/v1/classify/hs",
            json={"product": {"category": "confectionery"}},
            headers=api_key_header,
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["error"]["field"] == "product.name"

    def test_classify_invalid_country_code(self, client, api_key_header):
        """無効な国コード (422エラー)"""
        response = client.post(
            "/v1/classify/hs",
            json={"product": {"name": "Test product", "origin_country": "INVALID"}},
            headers=api_key_header,
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "violations" in data
        assert any(v["field"] == "product.origin_country" for v in data["violations"])

    def test_classify_invalid_ingredients_type(self, client, api_key_header):
        """ingredientsの型エラー (422エラー)"""
        response = client.post(
            "/v1/classify/hs",
            json={"product": {"name": "Test product", "ingredients": "not an array"}},
            headers=api_key_header,
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "violations" in data
        assert any(v["field"] == "product.ingredients" for v in data["violations"])

    def test_classify_no_matching_rules(self, client, api_key_header):
        """マッチするルールがない (422エラー)"""
        response = client.post(
            "/v1/classify/hs",
            json={
                "product": {
                    "name": "Unknown product",
                    "category": "unknown_category",
                    "ingredients": [
                        {"id": "ing_unknown_xyz", "pct": 100.0}
                    ],  # 有効だがルールにマッチしない
                }
            },
            headers=api_key_header,
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "violations" in data
        # バリデーションではなく、分類失敗のviolationを期待
        assert any(
            v.get("field") in ["classification", "product"] for v in data["violations"]
        )

    def test_classify_without_api_key(self, client):
        """APIキーなし (401エラー)"""
        response = client.post(
            "/v1/classify/hs", json={"product": {"name": "Test product"}}
        )

        # APIキー認証エラー
        assert response.status_code in [401, 403]

    def test_classify_review_required(self, client, api_key_header):
        """レビュー必須製品"""
        response = client.post(
            "/v1/classify/hs",
            json={
                "product": {
                    "name": "Other food preparation",
                    "category": "other_food_preparations",
                    "ingredients": [{"id": "ing_sugar", "pct": 50.0}],
                }
            },
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["review_required"] is True
        assert data["final_hs_code"] == "2106.90"

    def test_classify_with_trace_id_header(self, client, api_key_header):
        """X-Trace-IDヘッダーの使用"""
        headers = {**api_key_header, "X-Trace-ID": "CUSTOM-TRACE-ID"}

        response = client.post(
            "/v1/classify/hs",
            json={
                "product": {
                    "name": "Test product",
                    "ingredients": [{"id": "ing_wheat_flour", "pct": 35.0}],
                    "process": ["baking"],
                }
            },
            headers=headers,
        )

        assert response.status_code == 200

        # DB確認
        from app.db import db

        classification = (
            db.session.query(HSClassification)
            .filter_by(trace_id="CUSTOM-TRACE-ID")
            .first()
        )

        assert classification is not None

    @pytest.mark.postgres
    def test_classify_cache_hit(self, client, api_key_header):
        """キャッシュヒットの確認"""
        import uuid
        test_id = uuid.uuid4().hex[:8]
        payload = {
            "product": {
                "name": f"Cache Test Product {test_id}",
                "category": "confectionery",
                "ingredients": [{"id": "ing_wheat_flour", "pct": 40.0}],
                "process": ["baking"],
            }
        }

        # 1回目
        resp1 = client.post("/v1/classify/hs", json=payload, headers=api_key_header)
        data1 = resp1.get_json()
        assert data1["metadata"]["cache_hit"] is False

        # 2回目 (同じデータ)
        resp2 = client.post("/v1/classify/hs", json=payload, headers=api_key_header)
        data2 = resp2.get_json()
        assert data2["metadata"]["cache_hit"] is True
        assert data2["final_hs_code"] == data1["final_hs_code"]
