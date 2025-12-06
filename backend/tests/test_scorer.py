"""
スコアラーのユニットテスト
"""

import pytest
from app.classify.scorer import HSScorer


class TestHSScorer:
    """スコアラーのテスト"""
    
    def test_calculate_confidence_basic(self):
        """基本的な信頼度計算"""
        scorer = HSScorer()
        
        rule_matches = [
            {"weight": 0.8, "rule_id": "hs_food_001"},
        ]
        product_data = {
            "ingredients": [{"id": "ing_wheat_flour", "pct": 35.0}]
        }
        
        confidence = scorer.calculate_confidence(rule_matches, product_data)
        
        assert 0.0 <= confidence <= 1.0
        # base(0.3) + weight(0.8) * diversity(0.5) * ingredient(1.2) = 0.78
        assert confidence >= 0.70
    
    def test_calculate_confidence_multiple_rules(self):
        """複数ルールマッチ時の信頼度計算"""
        scorer = HSScorer()
        
        rule_matches = [
            {"weight": 0.8, "rule_id": "hs_food_001"},
            {"weight": 0.6, "rule_id": "hs_food_002"}
        ]
        product_data = {
            "ingredients": [{"id": "ing_wheat_flour", "pct": 35.0}]
        }
        
        confidence = scorer.calculate_confidence(rule_matches, product_data)
        
        assert confidence >= 0.80  # 複数ルールで高信頼度
    
    def test_calculate_confidence_no_ingredients(self):
        """成分なしの場合の信頼度計算"""
        scorer = HSScorer()
        
        rule_matches = [
            {"weight": 0.7, "rule_id": "hs_food_003"},
        ]
        product_data = {
            "ingredients": []
        }
        
        confidence = scorer.calculate_confidence(rule_matches, product_data)
        
        # 成分なしなので減点される (ingredient_factor = 0.8)
        assert confidence < 0.70
    
    def test_calculate_confidence_no_rules(self):
        """ルールマッチなしの場合"""
        scorer = HSScorer()
        
        confidence = scorer.calculate_confidence([], {})
        
        assert confidence == 0.0
    
    def test_rank_candidates(self):
        """候補ランキング"""
        scorer = HSScorer()
        
        candidates = [
            {"code": "1905.90", "confidence": 0.75},
            {"code": "1806.90", "confidence": 0.85},
            {"code": "1704.90", "confidence": 0.65}
        ]
        
        ranked = scorer.rank_candidates(candidates)
        
        # 信頼度順にソート
        assert ranked[0]["code"] == "1806.90"
        assert ranked[1]["code"] == "1905.90"
        assert ranked[2]["code"] == "1704.90"
        
        # raw_confidenceが保存されている
        assert ranked[0]["raw_confidence"] == 0.85
        assert ranked[1]["raw_confidence"] == 0.75
        
        # 2位以降は減衰が適用されている
        assert ranked[1]["confidence"] < ranked[1]["raw_confidence"]
        assert ranked[2]["confidence"] < ranked[2]["raw_confidence"]
        
        # rank_indexが設定されている
        assert ranked[0]["rank_index"] == 1
        assert ranked[1]["rank_index"] == 2
        assert ranked[2]["rank_index"] == 3
    
    def test_should_review_low_confidence(self):
        """低信頼度でレビュー必須"""
        scorer = HSScorer()
        
        top_candidate = {"confidence": 0.65, "raw_confidence": 0.65, "code": "1905.90"}
        rule_matches = []
        
        assert scorer.should_review(top_candidate, rule_matches) == True
    
    def test_should_review_high_confidence(self):
        """高信頼度でレビュー不要"""
        scorer = HSScorer()
        
        top_candidate = {"confidence": 0.85, "raw_confidence": 0.85, "code": "1905.90"}
        rule_matches = []
        
        assert scorer.should_review(top_candidate, rule_matches) == False
    
    def test_should_review_by_rule_flag(self):
        """ルールフラグでレビュー必須"""
        scorer = HSScorer()
        
        top_candidate = {"confidence": 0.85, "raw_confidence": 0.85, "code": "2106.90"}
        rule_matches = [
            {"requires_review": True, "rule_id": "hs_food_004"}
        ]
        
        assert scorer.should_review(top_candidate, rule_matches) == True
    
    def test_should_review_by_hs_code(self):
        """HSコード範囲でレビュー必須"""
        scorer = HSScorer()
        
        top_candidate = {"confidence": 0.85, "raw_confidence": 0.85, "code": "2106.90"}
        rule_matches = []
        
        assert scorer.should_review(top_candidate, rule_matches) == True
    
    def test_ingredient_factor_with_major_ingredient(self):
        """主要成分がある場合の調整係数"""
        scorer = HSScorer()
        
        product_data = {
            "ingredients": [
                {"id": "ing_wheat_flour", "pct": 40.0}
            ]
        }
        
        factor = scorer._calculate_ingredient_factor(product_data)
        assert factor == 1.2
    
    def test_ingredient_factor_without_major_ingredient(self):
        """主要成分がない場合の調整係数"""
        scorer = HSScorer()
        
        product_data = {
            "ingredients": [
                {"id": "ing_sugar", "pct": 20.0}
            ]
        }
        
        factor = scorer._calculate_ingredient_factor(product_data)
        assert factor == 1.0
    
    def test_ingredient_factor_no_ingredients(self):
        """成分なしの場合の調整係数"""
        scorer = HSScorer()
        
        product_data = {"ingredients": []}
        
        factor = scorer._calculate_ingredient_factor(product_data)
        assert factor == 0.8
    
    def test_get_thresholds(self):
        """閾値の取得"""
        scorer = HSScorer()
        
        assert scorer.get_min_confidence_threshold() == 0.60
        assert scorer.get_review_threshold() == 0.70
