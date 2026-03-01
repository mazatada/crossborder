"""
ルールエンジン - HS分類ルールの評価

このモジュールは、YAML形式で定義されたルールを読み込み、
商品データに対してルールを評価してHSコード候補を生成します。
"""

from typing import Dict, List, Any, Optional
import yaml
from pathlib import Path
import logging

from app.rules.predicates import PREDICATES, validate_predicate_params

logger = logging.getLogger(__name__)


class RuleValidationError(Exception):
    """ルール検証エラー"""

    pass


def _validate_conditions_structure(
    conditions: Dict,
    rule_id: str,
    valid_categories: List[str],
    valid_countries: List[str],
) -> None:
    if not isinstance(conditions, dict):
        raise RuleValidationError(f"Rule {rule_id}: conditions must be an object")

    for cond_type in ["all", "any"]:
        if cond_type in conditions:
            items = conditions.get(cond_type)
            if not isinstance(items, list):
                raise RuleValidationError(f"Rule {rule_id}: {cond_type} must be a list")
            for cond in items:
                if not isinstance(cond, dict):
                    raise RuleValidationError(
                        f"Rule {rule_id}: condition entries must be objects"
                    )
                for predicate, params in cond.items():
                    if predicate not in PREDICATES:
                        raise RuleValidationError(
                            f"Rule {rule_id}: Unknown predicate: {predicate}"
                        )

                    if not isinstance(params, dict):
                        raise RuleValidationError(
                            f"Rule {rule_id}: predicate params must be objects"
                        )
                    try:
                        validate_predicate_params(predicate, params)
                    except ValueError as e:
                        raise RuleValidationError(f"Rule {rule_id}: {e}") from e

                    # カテゴリ検証
                    if predicate == "category_is":
                        category = params.get("value", "")
                        if category and category not in valid_categories:
                            logger.warning(
                                f"Rule {rule_id}: Category '{category}' not in valid list"
                            )

                    # 国コード検証
                    if predicate == "origin_in":
                        countries = params.get("values", [])
                        if not isinstance(countries, list):
                            raise RuleValidationError(
                                f"Rule {rule_id}: origin_in.values must be a list"
                            )
                        for country in countries:
                            if country.upper() not in valid_countries:
                                logger.warning(
                                    f"Rule {rule_id}: Country '{country}' not in valid list"
                                )


class RuleValidator:
    """YAMLロードを伴わないDSLバリデータ"""

    def validate_conditions(self, conditions: Dict) -> None:
        valid_categories = [
            "confectionery",
            "beverages",
            "dairy",
            "meat",
            "seafood",
            "other_food_preparations",
        ]
        valid_countries = ["JP", "US", "CN", "KR", "TW", "TH", "VN"]
        _validate_conditions_structure(
            conditions, "custom", valid_categories, valid_countries
        )


class RuleEngine:
    """
    HS分類ルールエンジン

    YAML形式のルールファイルを読み込み、商品データに対してルールを評価します。
    述語ベースのDSLを使用して、柔軟なルール定義を可能にします。
    """

    def __init__(self, rules_dir: Optional[str] = None):
        target_dir: Path
        if rules_dir is None:
            # デフォルト: このファイルと同じディレクトリのrulesフォルダ
            target_dir = Path(__file__).parent
        else:
            target_dir = Path(rules_dir)
        self.rules_dir = target_dir
        self.rules: List[Dict] = []
        self.rules_version = "unknown"
        self.predicates: Dict[str, Any] = PREDICATES
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
            _validate_conditions_structure(
                conditions, rule["id"], valid_categories, valid_countries
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

    def get_rules_version(self) -> str:
        """ルールバージョンを取得"""
        return self.rules_version

    def get_rules_count(self) -> int:
        """ロード済みルール数を取得"""
        return len(self.rules)
