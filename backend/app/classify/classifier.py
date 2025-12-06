"""
分類器 - HS分類のメインロジック
"""

from typing import Dict, List, Any
import logging
from app.rules.engine import RuleEngine
from app.classify.scorer import HSScorer
from app.classify.explainer import HSExplainer

from app.classify.cache import HSCache

logger = logging.getLogger(__name__)


class ClassificationError(Exception):
    """分類エラー"""

    pass


class HSClassifier:
    """
    HS分類器

    ルールエンジンとスコアラーを使用して商品データを分類し、
    HSコード候補を生成します。
    """

    def __init__(self, rules_dir: str = None):
        self.rule_engine = RuleEngine(rules_dir)
        self.scorer = HSScorer()
        self.explainer = HSExplainer()
        self.cache = HSCache()
        self.min_confidence_threshold = self.scorer.get_min_confidence_threshold()

    def classify(self, product_data: Dict[str, Any]) -> Dict:
        """
        HS分類を実行

        Args:
            product_data: 商品データ (product オブジェクト)

        Returns:
            分類結果 (candidates, final_hs_code等)

        Raises:
            ClassificationError: 分類失敗時
        """
        # 1. キャッシュ確認
        rules_version = self.rule_engine.get_rules_version()
        cache_key = self.cache.generate_cache_key(product_data, rules_version)
        cached_result = self.cache.get(cache_key)

        if cached_result:
            logger.info(f"Cache hit for product: {product_data.get('name')}")
            cached_result["cache_hit"] = True
            return cached_result

        # 2. ルールマッチング
        rule_matches = self.rule_engine.evaluate(product_data)

        if not rule_matches:
            raise ClassificationError("No matching rules found")

        logger.info(
            f"Matched {len(rule_matches)} rules for product: {product_data.get('name', 'unknown')}"
        )

        # 3. HSコードごとにグループ化
        hs_groups: Dict[str, List[Dict[str, Any]]] = {}
        for match in rule_matches:
            hs_code = match["hs_code"]
            if hs_code not in hs_groups:
                hs_groups[hs_code] = []
            hs_groups[hs_code].append(match)

        # 4. 候補生成 (スコアラーを使用)
        candidates = []
        for hs_code, matches in hs_groups.items():
            # 改善版の信頼度計算
            confidence = self.scorer.calculate_confidence(matches, product_data)

            if confidence >= self.min_confidence_threshold:
                candidates.append(
                    {
                        "code": hs_code,
                        "description": matches[0]["description"],
                        "confidence": confidence,
                        "rationale": self._generate_rationale(matches, product_data),
                        "required_uom": matches[0].get("required_uom", "kg"),
                        "rule_matches": matches,
                    }
                )

        if not candidates:
            max_confidence = max(
                (
                    self.scorer.calculate_confidence(matches, product_data)
                    for matches in hs_groups.values()
                ),
                default=0.0,
            )
            raise ClassificationError(
                f"No candidates meet confidence threshold. "
                f"Max confidence: {max_confidence:.2f}, threshold: {self.min_confidence_threshold}"
            )

        # 5. ランキング (スコアラーを使用)
        ranked_candidates = self.scorer.rank_candidates(candidates)

        # 6. 最終結果
        top_candidate = ranked_candidates[0]

        result = {
            "hs_candidates": ranked_candidates,
            "final_hs_code": top_candidate["code"],
            "required_uom": top_candidate["required_uom"],
            "review_required": self.scorer.should_review(top_candidate, rule_matches),
            "rule_matches": rule_matches,
        }

        # Explaination生成
        result["explanations"] = self.explainer.explain(result, product_data)

        # キャッシュ保存
        self.cache.set(cache_key, result)
        result["cache_hit"] = False

        return result

    def _generate_rationale(self, matches: List[Dict], product_data: Dict) -> List[str]:
        """判断根拠を生成"""
        rationale = []

        # 成分ベース (含有率付き)
        ingredients = product_data.get("ingredients", [])
        if ingredients:
            # 含有率でソート
            sorted_ingredients = sorted(
                [
                    ing
                    for ing in ingredients
                    if isinstance(ing, dict) and ing.get("pct")
                ],
                key=lambda x: x.get("pct", 0),
                reverse=True,
            )

            if sorted_ingredients:
                primary = sorted_ingredients[0]
                rationale.append(
                    f"Primary ingredient: {primary['id']} ({primary.get('pct', 0)}%)"
                )
            else:
                # 含有率なしの場合
                primary_ids = [
                    ing.get("id") for ing in ingredients[:3] if isinstance(ing, dict)
                ]
                if primary_ids:
                    rationale.append(
                        f"Contains {', '.join(str(i) for i in primary_ids)}"
                    )

        # 加工方法ベース
        processes = product_data.get("process", [])
        if processes:
            rationale.append(f"{', '.join(processes)} process detected")

        # カテゴリベース
        category = product_data.get("category")
        if category:
            rationale.append(f"Category: {category}")

        # ルール名
        for match in matches[:2]:
            rationale.append(f"Matched rule: {match['rule_name']}")

        return rationale

    def get_rules_version(self) -> str:
        """ルールバージョンを取得"""
        return self.rule_engine.get_rules_version()
