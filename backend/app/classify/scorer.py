"""
スコアリングロジック - HS分類の信頼度計算とランキング

レビュー指摘を反映した改善版:
- base_confidenceを0.3に下げて厳格化
- 成分含有率による調整
- raw_confidenceの保持
- ビジネスルール考慮のレビュー判定
"""

from typing import List, Dict, Any
import math
import logging

logger = logging.getLogger(__name__)


class HSScorer:
    """
    HS分類スコアラー

    ルールマッチ結果から信頼度を計算し、候補をランキングします。
    """

    def __init__(self):
        # レビュー指摘を反映: base_confidenceを下げる
        self.base_confidence = 0.3  # 0.5 → 0.3
        self.rule_weight_multiplier = 1.0
        self.decay_factor = 0.15  # 0.1 → 0.15 (より強い減衰)
        self.min_confidence_threshold = 0.60  # 0.5 → 0.6
        self.review_threshold = 0.70  # 0.7 (変更なし)

    def calculate_confidence(
        self, rule_matches: List[Dict], product_data: Dict[str, Any]
    ) -> float:
        """
        信頼度を計算

        Args:
            rule_matches: マッチしたルールのリスト
            product_data: 商品データ

        Returns:
            信頼度スコア (0.0-1.0)
        """
        if not rule_matches:
            return 0.0

        # ルールの重みを合算
        total_weight = sum(m["weight"] for m in rule_matches)

        # マッチ数による調整 (ルールの多様性を考慮)
        unique_rule_types = len(set(m["rule_id"].split("_")[0] for m in rule_matches))
        match_diversity_factor = min(unique_rule_types / 2.0, 1.0)

        # 成分含有率による調整 (主要成分がある場合)
        ingredient_factor = self._calculate_ingredient_factor(product_data)

        # 最終信頼度
        confidence = min(
            self.base_confidence
            + (
                total_weight
                * self.rule_weight_multiplier
                * match_diversity_factor
                * ingredient_factor
            ),
            1.0,
        )

        logger.debug(
            f"Confidence calculation: base={self.base_confidence}, "
            f"total_weight={total_weight}, diversity={match_diversity_factor}, "
            f"ingredient={ingredient_factor}, final={confidence}"
        )

        return round(confidence, 2)

    def _calculate_ingredient_factor(self, product_data: Dict[str, Any]) -> float:
        """
        成分含有率による信頼度調整

        Args:
            product_data: 商品データ

        Returns:
            調整係数 (0.8-1.2)
        """
        ingredients = product_data.get("ingredients", [])
        if not ingredients:
            return 0.8  # 成分情報なしの場合は減点

        # 主要成分(30%以上)がある場合は加点
        has_major_ingredient = any(
            ing.get("pct", 0) >= 30.0 for ing in ingredients if isinstance(ing, dict)
        )

        return 1.2 if has_major_ingredient else 1.0

    def rank_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """
        候補をランキング (raw_confidenceを保持)

        Args:
            candidates: 候補リスト

        Returns:
            ランキング済み候補リスト
        """
        # 信頼度でソート
        ranked = sorted(candidates, key=lambda c: c["confidence"], reverse=True)

        # raw_confidenceを保存してから減衰適用
        for i, candidate in enumerate(ranked):
            candidate["raw_confidence"] = candidate["confidence"]
            candidate["rank_index"] = i + 1

            # 2位以降に減衰を適用
            if i > 0:
                decay = math.exp(-self.decay_factor * i)
                candidate["confidence"] = round(candidate["confidence"] * decay, 2)

        return ranked

    def should_review(self, top_candidate: Dict, rule_matches: List[Dict]) -> bool:
        """
        人間レビューが必要か判定 (ビジネスルール考慮)

        Args:
            top_candidate: 最上位候補
            rule_matches: マッチしたルールのリスト

        Returns:
            レビューが必要な場合True
        """
        # 1. 信頼度ベースの判定
        if (
            top_candidate.get("raw_confidence", top_candidate["confidence"])
            < self.review_threshold
        ):
            logger.info(
                f"Review required: confidence {top_candidate.get('raw_confidence')} "
                f"< threshold {self.review_threshold}"
            )
            return True

        # 2. ルールベースの判定 (requires_review フラグ)
        if any(m.get("requires_review", False) for m in rule_matches):
            review_rules = [
                m["rule_id"] for m in rule_matches if m.get("requires_review")
            ]
            logger.info(f"Review required by rules: {review_rules}")
            return True

        # 3. HSコード範囲ベースの判定 (例: 2106系は必ずレビュー)
        hs_code = top_candidate.get("code", "")
        if hs_code.startswith("2106"):
            logger.info(f"Review required for HS code range: {hs_code}")
            return True

        return False

    def get_min_confidence_threshold(self) -> float:
        """最小信頼度閾値を取得"""
        return self.min_confidence_threshold

    def get_review_threshold(self) -> float:
        """レビュー閾値を取得"""
        return self.review_threshold
