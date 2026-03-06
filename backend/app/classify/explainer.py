"""
HS分類の説明生成モジュール

分類結果の根拠を、多言語対応可能な構造化データとして生成します。
"""

from typing import List, Dict, Any


class HSExplainer:
    """
    HS分類結果の説明生成クラス
    """

    def explain(
        self, classification_result: Dict[str, Any], product_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        分類結果に対する詳細な説明を生成する

        Args:
            classification_result: Classifierからの出力結果 (hs_candidates等を含む)
            product_data: 入力された商品データ

        Returns:
            explanations: 構造化された説明リスト
            [
              {
                "id": "exp_ingredient_match",
                "template_key": "explanation.ingredient.match",
                "params": {"ingredient": "sugar", "pct": 50},
                "type": "supporting"
              },
              ...
            ]
        """
        explanations = []

        # 1. 決定されたHSコードの候補を取得（トップの候補）
        final_hs_code = classification_result.get("final_hs_code")
        if not final_hs_code:
            return []

        # トップ候補のルールマッチ情報を取得
        top_candidate = None
        candidates = classification_result.get("hs_candidates", [])
        for cand in candidates:
            if cand["code"] == final_hs_code:
                top_candidate = cand
                break

        if not top_candidate:
            return []

        rule_matches = top_candidate.get("rule_matches", [])

        # 2. ルールに基づく説明
        for match in rule_matches:
            rule_id = match.get("rule_id")
            description = match.get("description")

            explanations.append(
                {
                    "id": f"rule_match_{rule_id}",
                    "template_key": "explanation.rule.match",
                    "params": {"rule_id": rule_id, "description": description},
                    "type": "supporting",
                }
            )

        # 3. 成分に基づく説明
        ingredients = product_data.get("ingredients") or []
        for ing in ingredients:
            if isinstance(ing, dict):
                ing_id = ing.get("id")
                pct = ing.get("pct")

                # 主要成分(30%以上)の場合
                if pct and pct >= 30.0:
                    explanations.append(
                        {
                            "id": f"ingredient_major_{ing_id}",
                            "template_key": "explanation.ingredient.major",
                            "params": {"ingredient": ing_id, "percentage": pct},
                            "type": "supporting",
                        }
                    )
                # 特定の成分が含まれていること自体が重要な場合（ここでは簡易的に全てリスト化しないが、マッチしたルールに関係あるものを出すのが理想。今回は主要成分のみ）

        # 4. 加工方法に基づく説明
        processes = product_data.get("process") or []
        for proc in processes:
            explanations.append(
                {
                    "id": f"process_match_{proc}",
                    "template_key": "explanation.process.detected",
                    "params": {"process": proc},
                    "type": "supporting",
                }
            )

        # 5. カテゴリ
        category = product_data.get("category")
        if category:
            explanations.append(
                {
                    "id": "category_match",
                    "template_key": "explanation.category.match",
                    "params": {"category": category},
                    "type": "supporting",
                }
            )

        # 6. 信頼度に関する説明
        confidence = top_candidate.get("confidence", 0.0)
        explanations.append(
            {
                "id": "confidence_score",
                "template_key": "explanation.confidence.score",
                "params": {"score": confidence},
                "type": "info",
            }
        )

        # 7. レビュー要否
        review_required = classification_result.get("review_required", False)
        if review_required:
            explanations.append(
                {
                    "id": "review_required_alert",
                    "template_key": "explanation.review.required",
                    "params": {},
                    "type": "warning",
                }
            )

        return explanations

    def get_template_catalog(self) -> Dict[str, str]:
        """
        i18n用のデフォルト(英語)テンプレートカタログを返す
        （フロントエンド等で使用することを想定）
        """
        return {
            "explanation.rule.match": "Matched rule {rule_id}: {description}",
            "explanation.ingredient.major": "Contains major ingredient {ingredient} ({percentage}%)",
            "explanation.process.detected": "Manufacturing process '{process}' detected",
            "explanation.category.match": "Product category matches '{category}'",
            "explanation.confidence.score": "Confidence score: {score}",
            "explanation.review.required": "Manual review required due to low confidence or specific business rules",
        }
