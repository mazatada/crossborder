"""
HSExplainerのユニットテスト
"""

import pytest
from app.classify.explainer import HSExplainer


class TestHSExplainer:
    """Explainerのテスト"""
    
    def test_explain_basic(self):
        """基本的な説明生成テスト"""
        explainer = HSExplainer()
        
        # モックの分類結果
        classification_result = {
            "final_hs_code": "1905.90",
            "review_required": False,
            "hs_candidates": [
                {
                    "code": "1905.90",
                    "confidence": 0.85,
                    "rule_matches": [
                        {"rule_id": "rule_1", "description": "Cookie match"}
                    ]
                }
            ]
        }
        
        # モックの商品データ
        product_data = {
            "name": "Test Cookie",
            "category": "confectionery",
            "ingredients": [
                {"id": "wheat_flour", "pct": 40.0},
                {"id": "sugar", "pct": 20.0}
            ],
            "process": ["baking"]
        }
        
        explanations = explainer.explain(classification_result, product_data)
        
        # 検証
        assert len(explanations) > 0
        
        # 各種説明が含まれているか確認
        exp_ids = [e["id"] for e in explanations]
        assert "rule_match_rule_1" in exp_ids
        assert "ingredient_major_wheat_flour" in exp_ids
        assert "process_match_baking" in exp_ids
        assert "category_match" in exp_ids
        assert "confidence_score" in exp_ids
        
        # 構造の検証
        rule_exp = next(e for e in explanations if e["id"] == "rule_match_rule_1")
        assert rule_exp["template_key"] == "explanation.rule.match"
        assert rule_exp["params"]["rule_id"] == "rule_1"
        assert rule_exp["type"] == "supporting"

    def test_explain_review_required(self):
        """レビュー必須時の警告テスト"""
        explainer = HSExplainer()
        
        classification_result = {
            "final_hs_code": "2106.90",
            "review_required": True,
            "hs_candidates": [
                {"code": "2106.90", "confidence": 0.5, "rule_matches": []}
            ]
        }
        product_data = {}
        
        explanations = explainer.explain(classification_result, product_data)
        
        exp_ids = [e["id"] for e in explanations]
        assert "review_required_alert" in exp_ids
        
        alert = next(e for e in explanations if e["id"] == "review_required_alert")
        assert alert["type"] == "warning"

    def test_explain_no_match(self):
        """マッチなしの場合"""
        explainer = HSExplainer()
        
        classification_result = {
            "final_hs_code": None,
            "hs_candidates": []
        }
        product_data = {}
        
        explanations = explainer.explain(classification_result, product_data)
        assert len(explanations) == 0

    def test_catalog(self):
        """カタログ取得テスト"""
        explainer = HSExplainer()
        catalog = explainer.get_template_catalog()
        assert "explanation.rule.match" in catalog
