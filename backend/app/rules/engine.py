"""
ルールエンジン - HS分類ルールの評価

このモジュールは、YAML形式で定義されたルールを読み込み、
商品データに対してルールを評価してHSコード候補を生成します。
"""

from typing import Dict, List, Any, Optional
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class RuleValidationError(Exception):
    """ルール検証エラー"""

    pass


class RuleEngine:
    """
    HS分類ルールエンジン

    YAML形式のルールファイルを読み込み、商品データに対してルールを評価します。
    述語ベースのDSLを使用して、柔軟なルール定義を可能にします。
    """

    def __init__(self, rules_dir: str = None):
        if rules_dir is None:
            # デフォルト: このファイルと同じディレクトリのrulesフォルダ
            rules_dir = Path(__file__).parent
        self.rules_dir = Path(rules_dir)
        self.rules: List[Dict] = []
        self.rules_version = "unknown"
        self.predicates: Dict[str, Any] = {
            "contains_any_ids": self._contains_any_ids,
            "process_any": self._process_any,
            "origin_in": self._origin_in,
            "category_is": self._category_is,
            "not_contains_ids": self._not_contains_ids,
            "ingredient_pct_threshold": self._ingredient_pct_threshold,
            "always": self._always,
        }
        self.load_rules()
        self.validate_rules()

    def load_rules(self):
        """YAMLファイルからルールをロード"""
        if not self.rules_dir.exists():
            logger.warning(f"Rules directory not found: {self.rules_dir}")
            return

        for rule_file in self.rules_dir.glob("*.yml"):
            try:
                with open(rule_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    self.rules_version = data.get("version", "unknown")
                    loaded_rules = data.get("rules", [])
                    self.rules.extend(loaded_rules)
                    logger.info(
                        f"Loaded {len(loaded_rules)} rules from {rule_file.name}"
                    )
            except Exception as e:
                logger.error(f"Error loading rule file {rule_file}: {e}")
                raise

        # 優先度でソート
        self.rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
        logger.info(
            f"Total rules loaded: {len(self.rules)}, version: {self.rules_version}"
        )

    def validate_rules(self):
        """ルールの事前検証"""
        valid_categories = [
            "confectionery",
            "beverages",
            "dairy",
            "meat",
            "seafood",
            "other_food_preparations",
        ]
        valid_countries = ["JP", "US", "CN", "KR", "TW", "TH", "VN"]

        for rule in self.rules:
            # 必須フィールドチェック
            required_fields = [
                "id",
                "name",
                "hs_code",
                "priority",
                "weight",
                "conditions",
            ]
            for field in required_fields:
                if field not in rule:
                    raise RuleValidationError(
                        f"Rule {rule.get('id', 'unknown')} missing required field: {field}"
                    )

            # HSコード形式チェック
            hs_code = rule.get("hs_code", "")
            if not hs_code or not hs_code.replace(".", "").isdigit():
                raise RuleValidationError(
                    f"Rule {rule['id']}: Invalid HS code format: {hs_code}"
                )

            # 条件の検証
            conditions = rule.get("conditions", {})
            self._validate_conditions(
                conditions, rule["id"], valid_categories, valid_countries
            )

    def _validate_conditions(
        self,
        conditions: Dict,
        rule_id: str,
        valid_categories: List[str],
        valid_countries: List[str],
    ):
        """条件の検証"""
        for cond_type in ["all", "any"]:
            if cond_type in conditions:
                for cond in conditions[cond_type]:
                    for predicate, params in cond.items():
                        if predicate not in self.predicates:
                            raise RuleValidationError(
                                f"Rule {rule_id}: Unknown predicate: {predicate}"
                            )

                        # カテゴリ検証
                        if predicate == "category_is":
                            category = params.get("value", "")
                            if category not in valid_categories:
                                logger.warning(
                                    f"Rule {rule_id}: Category '{category}' not in valid list"
                                )

                        # 国コード検証
                        if predicate == "origin_in":
                            countries = params.get("values", [])
                            for country in countries:
                                if country.upper() not in valid_countries:
                                    logger.warning(
                                        f"Rule {rule_id}: Country '{country}' not in valid list"
                                    )

    def evaluate(self, product_data: Dict[str, Any]) -> List[Dict]:
        """
        商品データに対してルールを評価

        Args:
            product_data: 商品データ (product オブジェクト)

        Returns:
            マッチしたルールのリスト
        """
        matches = []

        for rule in self.rules:
            try:
                if self._evaluate_rule(rule, product_data):
                    matches.append(
                        {
                            "rule_id": rule["id"],
                            "rule_name": rule["name"],
                            "hs_code": rule["hs_code"],
                            "weight": rule.get("weight", 0.5),
                            "required_uom": rule.get("required_uom", "kg"),
                            "description": rule.get("description", ""),
                            "requires_review": rule.get("requires_review", False),
                            "effect": rule.get("effect", "include"),
                        }
                    )
            except Exception as e:
                logger.error(f"Error evaluating rule {rule['id']}: {e}")
                continue

        return matches

    def _evaluate_rule(self, rule: Dict, data: Dict) -> bool:
        """単一ルールの評価"""
        conditions = rule.get("conditions", {})

        # all条件
        if "all" in conditions:
            return all(self._evaluate_condition(c, data) for c in conditions["all"])

        # any条件
        if "any" in conditions:
            return any(self._evaluate_condition(c, data) for c in conditions["any"])

        return False

    def _evaluate_condition(self, condition: Dict, data: Dict) -> bool:
        """単一条件の評価"""
        # 述語名がキー
        for predicate, params in condition.items():
            if predicate not in self.predicates:
                raise ValueError(f"Unknown predicate: {predicate}")

            field = params.get("field")
            field_value = data.get(field) if field else None

            # 述語関数を呼び出し
            predicate_func = self.predicates[predicate]

            if "values" in params:
                return predicate_func(field_value, params["values"])
            elif "value" in params:
                return predicate_func(field_value, params["value"])
            elif predicate == "ingredient_pct_threshold":
                return predicate_func(
                    field_value,
                    params["ingredient_id"],
                    params["min_pct"],
                    params.get("max_pct"),
                )
            else:
                return predicate_func()

    # ========== 述語実装 ==========
        return False

    def _contains_any_ids(self, field_value: Any, values: List[str]) -> bool:
        """
        成分IDリストが指定IDのいずれかを含むか (完全一致)

        Args:
            field_value: 成分リスト [{"id": "ing_xxx", "pct": 30.0}, ...]
            values: 検索する成分IDリスト

        Returns:
            いずれかのIDが含まれる場合True
        """
        if not field_value:
            return False

        ingredient_ids = [ing.get("id") for ing in field_value if isinstance(ing, dict)]
        return any(ing_id in values for ing_id in ingredient_ids)

    def _process_any(self, field_value: Any, values: List[str]) -> bool:
        """
        加工方法が指定値のいずれかを含むか

        Args:
            field_value: 加工方法リスト ["baking", "packaging"]
            values: 検索する加工方法リスト

        Returns:
            いずれかの加工方法が含まれる場合True
        """
        if not field_value or not isinstance(field_value, list):
            return False

        processes = [p.lower() for p in field_value]
        return any(v.lower() in processes for v in values)

    def _origin_in(self, field_value: Any, values: List[str]) -> bool:
        """
        原産国が指定リストに含まれるか (ISO 3166-1 alpha-2)

        Args:
            field_value: 原産国コード (例: "JP")
            values: 許可される国コードリスト

        Returns:
            国コードがリストに含まれる場合True
        """
        if not field_value:
            return False
        return field_value.upper() in [v.upper() for v in values]

    def _category_is(self, field_value: Any, value: str) -> bool:
        """
        カテゴリが指定値と一致するか

        Args:
            field_value: カテゴリ名
            value: 期待されるカテゴリ名

        Returns:
            カテゴリが一致する場合True
        """
        if not field_value:
            return False
        return field_value.lower() == value.lower()

    def _not_contains_ids(self, field_value: Any, values: List[str]) -> bool:
        """
        成分IDリストが指定IDを含まないか

        Args:
            field_value: 成分リスト
            values: 除外する成分IDリスト

        Returns:
            いずれのIDも含まない場合True
        """
        return not self._contains_any_ids(field_value, values)

    def _ingredient_pct_threshold(
        self,
        field_value: Any,
        ingredient_id: str,
        min_pct: float,
        max_pct: Optional[float] = None,
    ) -> bool:
        """
        特定成分の含有率が閾値範囲内か

        Args:
            field_value: 成分リスト
            ingredient_id: 対象成分ID
            min_pct: 最小含有率 (%)
            max_pct: 最大含有率 (%) (Noneの場合は上限なし)

        Returns:
            含有率が範囲内の場合True
        """
        if not field_value:
            return False

        for ing in field_value:
            if isinstance(ing, dict) and ing.get("id") == ingredient_id:
                pct = ing.get("pct", 0)
                if max_pct is None:
                    return pct >= min_pct
                return min_pct <= pct <= max_pct

        return False

    def _always(self) -> bool:
        """
        常に真 (デフォルトルール用)

        Returns:
            常にTrue
        """
        return True

    def get_rules_version(self) -> str:
        """ルールバージョンを取得"""
        return self.rules_version

    def get_rules_count(self) -> int:
        """ロード済みルール数を取得"""
        return len(self.rules)
