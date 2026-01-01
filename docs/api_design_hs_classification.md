# HS分類API 詳細設計書 (改訂版)

**バージョン**: 2.0  
**作成日**: 2025-12-05  
**改訂日**: 2025-12-05  
**対象**: Phase 4-2 HS分類API実装

---

## 📋 改訂履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| 1.0 | 2025-12-05 | 初版作成 |
| 2.0 | 2025-12-05 | レビュー指摘を反映。既存OpenAPI仕様との完全整合、エラー形式統一、DSL統一、キャッシュ戦略改善 |

---

## 📋 目次

1. [概要](#概要)
2. [API仕様 (既存OpenAPIとの完全整合)](#api仕様)
3. [ルールエンジン設計](#ルールエンジン設計)
4. [スコアリングロジック](#スコアリングロジック)
5. [説明可能性](#説明可能性)
6. [データモデル](#データモデル)
7. [エラーハンドリング](#エラーハンドリング)
8. [キャッシュ戦略](#キャッシュ戦略)
9. [テスト計画](#テスト計画)
10. [実装タスク](#実装タスク)

---

## 概要

### 目的
商品情報からHSコード(Harmonized System Code)を自動分類し、信頼度スコアと判断根拠を提供する。

### 要件
- **精度**: 代表50品目でリコール≥80%
- **性能**: P95 ≤ 300ms (キャッシュ/ルールのみ時)
- **説明可能性**: 判断根拠を明示
- **拡張性**: AI/ルールの切替可能

### 設計原則
1. **既存仕様との完全整合**: OpenAPI、エラー形式、DSLを既存仕様に合わせる
2. **ルールベース優先**: 明確なルールで分類可能なものはルールで処理
3. **説明可能性**: 全ての判断に根拠を記録
4. **段階的信頼度**: 複数候補をスコア付きで提示
5. **監査可能**: 全ての分類結果を記録

---

## API仕様

> **重要**: 本仕様は既存の [`openapi.yaml`](file:///d:/works2025/越境EC/crossover_win/crossborder/backend/openapi.yaml) と完全に整合しています。

### エンドポイント

```
POST /v1/classify/hs
```

### リクエスト

#### ヘッダー
```
Content-Type: application/json
Authorization: Bearer {api_key}
X-Trace-ID: {trace_id}  (オプション)
```

#### ボディ (既存OpenAPI準拠)

```json
{
  "product": {
    "name": "Chocolate cookies",
    "category": "confectionery",
    "process": ["baking", "packaging"],
    "origin_country": "JP",
    "ingredients": [
      { "id": "ing_wheat_flour", "pct": 30.0 },
      { "id": "ing_sugar", "pct": 25.0 },
      { "id": "ing_cocoa", "pct": 15.0 },
      { "id": "ing_eggs", "pct": 10.0 }
    ]
  },
  "traceId": "TRACE-HS-001"
}
```

#### フィールド定義

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `product` | object | ✓ | 商品情報 |
| `product.name` | string | ✓ | 商品名 (英語推奨) |
| `product.category` | string | - | 商品カテゴリ |
| `product.process` | array[string] | - | 加工方法リスト |
| `product.origin_country` | string | - | 原産国 (ISO 3166-1 alpha-2) |
| `product.ingredients` | array[object] | - | 成分リスト (canonical ingredient ID) |
| `product.ingredients[].id` | string | ✓ | 成分ID (例: `ing_wheat_flour`) |
| `product.ingredients[].pct` | number | - | 含有率 (%) |
| `traceId` | string | - | トレースID |

### レスポンス (既存OpenAPI準拠 + 拡張)

#### 成功 (200 OK)
```json
{
  "hs_candidates": [
    {
      "code": "1905.90",
      "description": "Bread, pastry, cakes, biscuits and other bakers' wares",
      "confidence": 0.75,
      "rationale": [
        "Primary ingredient: wheat flour (30%)",
        "Baking process detected",
        "Category: confectionery"
      ],
      "required_uom": "kg",
      "rule_matches": [
        {
          "rule_id": "hs_food_001",
          "rule_name": "Wheat-based baked goods",
          "weight": 0.8
        }
      ]
    },
    {
      "code": "1806.90",
      "description": "Chocolate and other food preparations containing cocoa",
      "confidence": 0.58,
      "rationale": [
        "Contains cocoa (15%)",
        "Category: confectionery"
      ],
      "required_uom": "kg",
      "rule_matches": [
        {
          "rule_id": "hs_food_002",
          "rule_name": "Cocoa-containing products",
          "weight": 0.6
        }
      ]
    }
  ],
  "final_hs_code": "1905.90",
  "duty_rate": {
    "ad_valorem_pct": 0.0,
    "additional": []
  },
  "risk_flags": {
    "ad_cvd": false,
    "import_alert": false
  },
  "quota_applicability": null,
  "review_required": false,
  "explanations": [
    {
      "type": "primary_ingredient",
      "description": "Wheat flour is the primary ingredient (30%), indicating HS 1905 category",
      "rule_ids": ["hs_food_001"],
      "template_key": "primary_ingredient",
      "params": {
        "ingredient": "wheat flour",
        "pct": 30.0,
        "hs_category": "1905"
      }
    },
    {
      "type": "process",
      "description": "Baking process confirms classification as baked goods",
      "rule_ids": ["hs_food_001"],
      "template_key": "process_confirmation",
      "params": {
        "process": "baking",
        "category": "baked goods"
      }
    }
  ],
  "metadata": {
    "classification_method": "rule_based",
    "processing_time_ms": 45,
    "cache_hit": false,
    "rules_version": "1.0.0"
  }
}
```

#### エラー (400 Bad Request) - 既存エラー形式準拠

```json
{
  "error": {
    "class": "missing_required",
    "message": "product.name is required",
    "field": "product.name",
    "severity": "block"
  }
}
```

#### エラー (422 Unprocessable Entity) - 既存エラー形式準拠

```json
{
  "violations": [
    {
      "field": "product.origin_country",
      "rule": "iso_3166_1_alpha_2",
      "message": "Invalid country code: 'XYZ'. Must be ISO 3166-1 alpha-2 format."
    },
    {
      "field": "classification",
      "rule": "min_confidence",
      "message": "Unable to classify with sufficient confidence. Max confidence: 0.45, threshold: 0.60. Please provide more detailed product information."
    }
  ]
}
```

---

## ルールエンジン設計

### ルールDSL (既存仕様準拠)

> **重要**: 既存バックエンド仕様のDSL形式に合わせ、述語名をキーに持つ形式を採用します。

#### ルールファイル構造
```yaml
# rules/hs_food.yml
version: "1.0.0"
category: "food"
metadata:
  description: "Food products HS classification rules"
  last_updated: "2025-12-05"

rules:
  - id: "hs_food_001"
    name: "Wheat-based baked goods"
    hs_code: "1905.90"
    description: "Bread, pastry, cakes, biscuits and other bakers' wares"
    priority: 10
    weight: 0.8
    required_uom: "kg"
    requires_review: false
    effect: "include"
    conditions:
      all:
        - contains_any_ids:
            field: "ingredients"
            values: ["ing_wheat_flour", "ing_flour", "ing_wheat"]
        - process_any:
            field: "process"
            values: ["baking", "baked"]
    
  - id: "hs_food_002"
    name: "Cocoa-containing products"
    hs_code: "1806.90"
    description: "Chocolate and other food preparations containing cocoa"
    priority: 8
    weight: 0.6
    required_uom: "kg"
    requires_review: false
    effect: "include"
    conditions:
      any:
        - contains_any_ids:
            field: "ingredients"
            values: ["ing_cocoa", "ing_chocolate", "ing_cacao"]
    
  - id: "hs_food_003"
    name: "Sugar confectionery (no cocoa)"
    hs_code: "1704.90"
    description: "Sugar confectionery not containing cocoa"
    priority: 7
    weight: 0.7
    required_uom: "kg"
    requires_review: false
    effect: "include"
    conditions:
      all:
        - category_is:
            field: "category"
            value: "confectionery"
        - not_contains_ids:
            field: "ingredients"
            values: ["ing_cocoa", "ing_chocolate"]
  
  - id: "hs_food_004"
    name: "High-risk category - requires review"
    hs_code: "2106.90"
    description: "Food preparations not elsewhere specified"
    priority: 5
    weight: 0.5
    required_uom: "kg"
    requires_review: true  # 必ず人間レビュー
    effect: "include"
    conditions:
      any:
        - category_is:
            field: "category"
            value: "other_food_preparations"
```

### 述語 (Predicates)

#### 実装する述語

1. **contains_any_ids** (ID完全一致)
   ```python
   def contains_any_ids(field_value: list, values: list) -> bool:
       """成分IDリストが指定IDのいずれかを含むか (完全一致)"""
       if not field_value:
           return False
       ingredient_ids = [ing.get("id") for ing in field_value if isinstance(ing, dict)]
       return any(ing_id in values for ing_id in ingredient_ids)
   ```

2. **process_any**
   ```python
   def process_any(field_value: list, values: list) -> bool:
       """加工方法が指定値のいずれかを含むか"""
       if not field_value or not isinstance(field_value, list):
           return False
       processes = [p.lower() for p in field_value]
       return any(v.lower() in processes for v in values)
   ```

3. **origin_in**
   ```python
   def origin_in(field_value: str, values: list) -> bool:
       """原産国が指定リストに含まれるか (ISO 3166-1 alpha-2)"""
       if not field_value:
           return False
       return field_value.upper() in [v.upper() for v in values]
   ```

4. **category_is**
   ```python
   def category_is(field_value: str, value: str) -> bool:
       """カテゴリが指定値と一致するか"""
       if not field_value:
           return False
       return field_value.lower() == value.lower()
   ```

5. **not_contains_ids**
   ```python
   def not_contains_ids(field_value: list, values: list) -> bool:
       """成分IDリストが指定IDを含まないか"""
       return not contains_any_ids(field_value, values)
   ```

6. **ingredient_pct_threshold**
   ```python
   def ingredient_pct_threshold(field_value: list, ingredient_id: str, min_pct: float, max_pct: float = None) -> bool:
       """特定成分の含有率が閾値範囲内か"""
       if not field_value:
           return False
       for ing in field_value:
           if isinstance(ing, dict) and ing.get("id") == ingredient_id:
               pct = ing.get("pct", 0)
               if max_pct is None:
                   return pct >= min_pct
               return min_pct <= pct <= max_pct
       return False
   ```

7. **always**
   ```python
   def always() -> bool:
       """常に真 (デフォルトルール用)"""
       return True
   ```

### ルールエンジン実装

```python
# backend/app/rules/engine.py

from typing import Dict, List, Any
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class RuleValidationError(Exception):
    """ルール検証エラー"""
    pass

class RuleEngine:
    def __init__(self, rules_dir: str = "rules"):
        self.rules_dir = Path(rules_dir)
        self.rules: List[Dict] = []
        self.rules_version = "unknown"
        self.predicates = {
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
        for rule_file in self.rules_dir.glob("*.yml"):
            with open(rule_file, encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self.rules_version = data.get("version", "unknown")
                self.rules.extend(data.get("rules", []))
                logger.info(f"Loaded {len(data.get('rules', []))} rules from {rule_file}")
        
        # 優先度でソート
        self.rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
        logger.info(f"Total rules loaded: {len(self.rules)}, version: {self.rules_version}")
    
    def validate_rules(self):
        """ルールの事前検証"""
        valid_categories = ["confectionery", "beverages", "dairy", "meat", "seafood", "other_food_preparations"]
        valid_countries = ["JP", "US", "CN", "KR", "TW", "TH", "VN"]  # 拡張可能
        
        for rule in self.rules:
            # 必須フィールドチェック
            required_fields = ["id", "name", "hs_code", "priority", "weight", "conditions"]
            for field in required_fields:
                if field not in rule:
                    raise RuleValidationError(f"Rule {rule.get('id', 'unknown')} missing required field: {field}")
            
            # HSコード形式チェック
            hs_code = rule.get("hs_code", "")
            if not hs_code or not hs_code.replace(".", "").isdigit():
                raise RuleValidationError(f"Rule {rule['id']}: Invalid HS code format: {hs_code}")
            
            # カテゴリ検証 (category_is述語使用時)
            conditions = rule.get("conditions", {})
            self._validate_conditions(conditions, rule['id'], valid_categories, valid_countries)
    
    def _validate_conditions(self, conditions: Dict, rule_id: str, valid_categories: List[str], valid_countries: List[str]):
        """条件の検証"""
        for cond_type in ["all", "any"]:
            if cond_type in conditions:
                for cond in conditions[cond_type]:
                    for predicate, params in cond.items():
                        if predicate not in self.predicates:
                            raise RuleValidationError(f"Rule {rule_id}: Unknown predicate: {predicate}")
                        
                        # カテゴリ検証
                        if predicate == "category_is":
                            category = params.get("value", "")
                            if category not in valid_categories:
                                logger.warning(f"Rule {rule_id}: Category '{category}' not in valid list")
                        
                        # 国コード検証
                        if predicate == "origin_in":
                            countries = params.get("values", [])
                            for country in countries:
                                if country.upper() not in valid_countries:
                                    logger.warning(f"Rule {rule_id}: Country '{country}' not in valid list")
    
    def evaluate(self, product_data: Dict[str, Any]) -> List[Dict]:
        """商品データに対してルールを評価"""
        matches = []
        
        for rule in self.rules:
            try:
                if self._evaluate_rule(rule, product_data):
                    matches.append({
                        "rule_id": rule["id"],
                        "rule_name": rule["name"],
                        "hs_code": rule["hs_code"],
                        "weight": rule.get("weight", 0.5),
                        "required_uom": rule.get("required_uom", "kg"),
                        "description": rule.get("description", ""),
                        "requires_review": rule.get("requires_review", False),
                        "effect": rule.get("effect", "include"),
                    })
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
                    params.get("max_pct")
                )
            else:
                return predicate_func()
    
    # 述語実装
    def _contains_any_ids(self, field_value, values):
        """成分IDリストが指定IDのいずれかを含むか"""
        if not field_value:
            return False
        ingredient_ids = [ing.get("id") for ing in field_value if isinstance(ing, dict)]
        return any(ing_id in values for ing_id in ingredient_ids)
    
    def _process_any(self, field_value, values):
        """加工方法が指定値のいずれかを含むか"""
        if not field_value or not isinstance(field_value, list):
            return False
        processes = [p.lower() for p in field_value]
        return any(v.lower() in processes for v in values)
    
    def _origin_in(self, field_value, values):
        """原産国が指定リストに含まれるか"""
        if not field_value:
            return False
        return field_value.upper() in [v.upper() for v in values]
    
    def _category_is(self, field_value, value):
        """カテゴリが指定値と一致するか"""
        if not field_value:
            return False
        return field_value.lower() == value.lower()
    
    def _not_contains_ids(self, field_value, values):
        """成分IDリストが指定IDを含まないか"""
        return not self._contains_any_ids(field_value, values)
    
    def _ingredient_pct_threshold(self, field_value, ingredient_id, min_pct, max_pct=None):
        """特定成分の含有率が閾値範囲内か"""
        if not field_value:
            return False
        for ing in field_value:
            if isinstance(ing, dict) and ing.get("id") == ingredient_id:
                pct = ing.get("pct", 0)
                if max_pct is None:
                    return pct >= min_pct
                return min_pct <= pct <= max_pct
        return False
    
    def _always(self):
        """常に真"""
        return True
```

---

## スコアリングロジック

### 信頼度計算アルゴリズム (改善版)

> **レビュー指摘対応**: base_confidenceを下げ、閾値を上げて、より厳格な判定を実現

```python
# backend/app/classify/scorer.py

from typing import List, Dict
import math
import logging

logger = logging.getLogger(__name__)

class HSScorer:
    def __init__(self):
        # レビュー指摘を反映: base_confidenceを下げる
        self.base_confidence = 0.3  # 0.5 → 0.3
        self.rule_weight_multiplier = 1.0
        self.decay_factor = 0.15  # 0.1 → 0.15 (より強い減衰)
        self.min_confidence_threshold = 0.60  # 0.5 → 0.6
        self.review_threshold = 0.70  # 0.7 (変更なし)
    
    def calculate_confidence(
        self, 
        rule_matches: List[Dict],
        product_data: Dict
    ) -> float:
        """信頼度を計算"""
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
            self.base_confidence + 
            (total_weight * self.rule_weight_multiplier * match_diversity_factor * ingredient_factor),
            1.0
        )
        
        logger.debug(f"Confidence calculation: base={self.base_confidence}, "
                    f"total_weight={total_weight}, diversity={match_diversity_factor}, "
                    f"ingredient={ingredient_factor}, final={confidence}")
        
        return round(confidence, 2)
    
    def _calculate_ingredient_factor(self, product_data: Dict) -> float:
        """成分含有率による信頼度調整"""
        ingredients = product_data.get("ingredients", [])
        if not ingredients:
            return 0.8  # 成分情報なしの場合は減点
        
        # 主要成分(30%以上)がある場合は加点
        has_major_ingredient = any(
            ing.get("pct", 0) >= 30.0 
            for ing in ingredients 
            if isinstance(ing, dict)
        )
        
        return 1.2 if has_major_ingredient else 1.0
    
    def rank_candidates(
        self, 
        candidates: List[Dict]
    ) -> List[Dict]:
        """候補をランキング (raw_confidenceを保持)"""
        # 信頼度でソート
        ranked = sorted(
            candidates,
            key=lambda c: c["confidence"],
            reverse=True
        )
        
        # raw_confidenceを保存してから減衰適用
        for i, candidate in enumerate(ranked):
            candidate["raw_confidence"] = candidate["confidence"]
            candidate["rank_index"] = i + 1
            
            # 2位以降に減衰を適用
            if i > 0:
                decay = math.exp(-self.decay_factor * i)
                candidate["confidence"] = round(
                    candidate["confidence"] * decay,
                    2
                )
        
        return ranked
    
    def should_review(
        self, 
        top_candidate: Dict,
        rule_matches: List[Dict]
    ) -> bool:
        """人間レビューが必要か判定 (ビジネスルール考慮)"""
        # 1. 信頼度ベースの判定
        if top_candidate["confidence"] < self.review_threshold:
            return True
        
        # 2. ルールベースの判定 (requires_review フラグ)
        if any(m.get("requires_review", False) for m in rule_matches):
            logger.info(f"Review required by rule: {[m['rule_id'] for m in rule_matches if m.get('requires_review')]}")
            return True
        
        # 3. HSコード範囲ベースの判定 (例: 2106系は必ずレビュー)
        hs_code = top_candidate.get("code", "")
        if hs_code.startswith("2106"):
            logger.info(f"Review required for HS code range: {hs_code}")
            return True
        
        return False
```

---

## 説明可能性

### Explanationsフィールド (i18n対応)

> **レビュー指摘対応**: template_key + params で多言語対応を容易に

```python
# backend/app/classify/explainer.py

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class HSExplainer:
    def generate_explanations(
        self,
        product_data: Dict,
        candidates: List[Dict],
        rule_matches: List[Dict]
    ) -> List[Dict]:
        """説明を生成 (i18n対応)"""
        explanations = []
        
        if not candidates:
            return explanations
        
        top_candidate = candidates[0]
        ingredients = product_data.get("ingredients", [])
        
        # 主要成分の説明
        if ingredients:
            # 含有率でソート
            sorted_ingredients = sorted(
                [ing for ing in ingredients if isinstance(ing, dict) and ing.get("pct")],
                key=lambda x: x.get("pct", 0),
                reverse=True
            )
            
            if sorted_ingredients:
                primary = sorted_ingredients[0]
                explanations.append({
                    "type": "primary_ingredient",
                    "description": f"{primary['id']} is the primary ingredient ({primary.get('pct', 0)}%), "
                                  f"indicating HS {top_candidate['code'][:4]} category",
                    "rule_ids": [m["rule_id"] for m in rule_matches if primary['id'] in str(m)],
                    "template_key": "primary_ingredient",
                    "params": {
                        "ingredient_id": primary['id'],
                        "pct": primary.get('pct', 0),
                        "hs_category": top_candidate['code'][:4]
                    }
                })
        
        # 加工方法の説明
        processes = product_data.get("process", [])
        if processes:
            primary_process = processes[0]
            explanations.append({
                "type": "process",
                "description": f"{primary_process} process confirms classification as "
                              f"{top_candidate.get('description', '')}",
                "rule_ids": [m["rule_id"] for m in rule_matches if primary_process.lower() in str(m).lower()],
                "template_key": "process_confirmation",
                "params": {
                    "process": primary_process,
                    "category": top_candidate.get('description', '')
                }
            })
        
        # カテゴリの説明
        category = product_data.get("category")
        if category:
            explanations.append({
                "type": "category",
                "description": f"Product category '{category}' aligns with HS code {top_candidate['code']}",
                "rule_ids": [m["rule_id"] for m in rule_matches if category.lower() in str(m).lower()],
                "template_key": "category_alignment",
                "params": {
                    "category": category,
                    "hs_code": top_candidate['code']
                }
            })
        
        # 信頼度の説明
        if top_candidate["confidence"] < 0.7:
            explanations.append({
                "type": "confidence_warning",
                "description": f"Confidence score {top_candidate['confidence']} is below threshold, "
                              f"manual review recommended",
                "rule_ids": [],
                "template_key": "confidence_warning",
                "params": {
                    "confidence": top_candidate['confidence'],
                    "threshold": 0.7
                }
            })
        
        # レビュー必須の説明
        if any(m.get("requires_review", False) for m in rule_matches):
            review_rules = [m["rule_id"] for m in rule_matches if m.get("requires_review")]
            explanations.append({
                "type": "review_required",
                "description": f"Manual review required by classification rules: {', '.join(review_rules)}",
                "rule_ids": review_rules,
                "template_key": "review_required_by_rule",
                "params": {
                    "rule_ids": review_rules
                }
            })
        
        return explanations
```

---

## データモデル

### hs_classifications テーブル (拡張版)

```python
# backend/app/models.py (追加)

from datetime import datetime
from app.db import db

class HSClassification(db.Model):
    __tablename__ = "hs_classifications"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.String(128), index=True, nullable=True)
    trace_id = db.Column(db.String(64), index=True, nullable=False)
    
    # 入力データ (product object)
    product_name = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(64), nullable=True, index=True)
    origin_country = db.Column(db.String(2), nullable=True)
    ingredients = db.Column(db.JSON, nullable=True)  # [{"id": "ing_xxx", "pct": 30.0}]
    process = db.Column(db.JSON, nullable=True)  # ["baking", "packaging"]
    
    # 分類結果 (hs_candidates)
    hs_candidates = db.Column(db.JSON, nullable=False)  # 全候補 (OpenAPI準拠)
    final_hs_code = db.Column(db.String(16), nullable=False, index=True)
    required_uom = db.Column(db.String(8), nullable=False)
    review_required = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # 拡張フィールド
    duty_rate = db.Column(db.JSON, nullable=True)
    risk_flags = db.Column(db.JSON, nullable=True)
    quota_applicability = db.Column(db.String(64), nullable=True)
    explanations = db.Column(db.JSON, nullable=True)
    
    # メタデータ
    classification_method = db.Column(db.String(32), default="rule_based")
    processing_time_ms = db.Column(db.Integer, nullable=True)
    cache_hit = db.Column(db.Boolean, default=False)
    rules_version = db.Column(db.String(16), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<HSClassification {self.id} hs={self.final_hs_code} trace={self.trace_id}>"
```

### マイグレーション

```python
# backend/migrations/versions/YYYYMMDD_add_hs_classifications.py

"""add hs_classifications table

Revision ID: xxxxx
Revises: xxxxx
Create Date: 2025-12-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'hs_classifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.String(length=128), nullable=True),
        sa.Column('trace_id', sa.String(length=64), nullable=False),
        sa.Column('product_name', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('origin_country', sa.String(length=2), nullable=True),
        sa.Column('ingredients', sa.JSON(), nullable=True),
        sa.Column('process', sa.JSON(), nullable=True),
        sa.Column('hs_candidates', sa.JSON(), nullable=False),
        sa.Column('final_hs_code', sa.String(length=16), nullable=False),
        sa.Column('required_uom', sa.String(length=8), nullable=False),
        sa.Column('review_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('duty_rate', sa.JSON(), nullable=True),
        sa.Column('risk_flags', sa.JSON(), nullable=True),
        sa.Column('quota_applicability', sa.String(length=64), nullable=True),
        sa.Column('explanations', sa.JSON(), nullable=True),
        sa.Column('classification_method', sa.String(length=32), nullable=True, server_default='rule_based'),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('cache_hit', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('rules_version', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # インデックス
    op.create_index('ix_hs_classifications_trace_id', 'hs_classifications', ['trace_id'])
    op.create_index('ix_hs_classifications_product_id', 'hs_classifications', ['product_id'])
    op.create_index('ix_hs_classifications_final_hs_code', 'hs_classifications', ['final_hs_code'])
    op.create_index('ix_hs_classifications_category', 'hs_classifications', ['category'])
    op.create_index('ix_hs_classifications_review_required', 'hs_classifications', ['review_required'])

def downgrade():
    op.drop_index('ix_hs_classifications_review_required', table_name='hs_classifications')
    op.drop_index('ix_hs_classifications_category', table_name='hs_classifications')
    op.drop_index('ix_hs_classifications_final_hs_code', table_name='hs_classifications')
    op.drop_index('ix_hs_classifications_product_id', table_name='hs_classifications')
    op.drop_index('ix_hs_classifications_trace_id', table_name='hs_classifications')
    op.drop_table('hs_classifications')
```

---

## エラーハンドリング

> **重要**: 既存の共通エラーラッパを使用し、エラーコードを既存カタログに合わせます。

### エラーコード (既存カタログ準拠)

| HTTPステータス | error.class | 説明 | 実装での使用例 |
|---------------|-------------|------|---------------|
| 400 | `missing_required` | 必須フィールド不足 | `product.name`がない |
| 400 | `invalid_format` | フォーマット不正 | 国コードが不正 |
| 422 | `validation_failed` | バリデーション違反 | 複数の検証エラー |
| 422 | `classification_failed` | 分類失敗 | 信頼度不足 |
| 500 | `rule_engine_error` | ルールエンジンエラー | ルール評価失敗 |

### エラーレスポンス実装

```python
# backend/app/api/v1_classify.py (エラーハンドリング部分)

from flask import jsonify
from app.errors import AppError

# 400エラー
def handle_missing_required(field: str):
    return jsonify({
        "error": {
            "class": "missing_required",
            "message": f"{field} is required",
            "field": field,
            "severity": "block"
        }
    }), 400

# 422エラー (バリデーション違反)
def handle_validation_errors(violations: List[Dict]):
    return jsonify({
        "violations": violations
    }), 422

# 422エラー (分類失敗)
def handle_classification_failed(max_confidence: float, threshold: float):
    return jsonify({
        "violations": [{
            "field": "classification",
            "rule": "min_confidence",
            "message": f"Unable to classify with sufficient confidence. "
                      f"Max confidence: {max_confidence}, threshold: {threshold}. "
                      f"Please provide more detailed product information."
        }]
    }), 422
```

---

## キャッシュ戦略

> **レビュー指摘対応**: ルールバージョンをキーに含め、Redis対応を見据えた設計

### キャッシュキー生成 (改善版)

```python
import hashlib
import json
from typing import Dict

def generate_cache_key(product_data: Dict, rules_version: str) -> str:
    """キャッシュキーを生成 (ルールバージョン含む)"""
    # 正規化
    ingredients = product_data.get("ingredients", [])
    # 成分は最大10個まで (キー肥大化防止)
    limited_ingredients = sorted(
        [ing.get("id") for ing in ingredients[:10] if isinstance(ing, dict)],
        key=str
    )
    
    normalized = {
        "name": product_data.get("name", "").lower().strip()[:100],  # 100文字まで
        "category": product_data.get("category", "").lower(),
        "origin": product_data.get("origin_country", "").upper(),
        "ingredients": limited_ingredients,
        "process": sorted([p.lower() for p in product_data.get("process", [])[:5]]),  # 5個まで
        "rules_version": rules_version,  # ルールバージョンを含める
    }
    
    # ハッシュ化
    key_str = json.dumps(normalized, sort_keys=True)
    return f"hs_classify:{hashlib.sha256(key_str.encode()).hexdigest()}"
```

### キャッシュ実装 (Redis対応可能)

```python
# backend/app/classify/cache.py

from typing import Dict, Optional
from abc import ABC, abstractmethod
import json
import logging

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
        self.cache = {}
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
            # LRU削除 (簡易実装)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"Cache eviction: {oldest_key}")
        
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
            "max_size": self.max_size
        }

class RedisCache(CacheBackend):
    """Redisキャッシュ (本番・スケールアウト用)"""
    
    def __init__(self, redis_client, ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = ttl
    
    def get(self, key: str) -> Optional[Dict]:
        value = self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    def set(self, key: str, value: Dict, ttl: int = None):
        ttl = ttl or self.default_ttl
        self.redis.setex(key, ttl, json.dumps(value))
    
    def delete(self, key: str):
        self.redis.delete(key)
    
    def clear(self):
        # 注意: 全キー削除は危険なので、プレフィックス付きキーのみ削除
        for key in self.redis.scan_iter("hs_classify:*"):
            self.redis.delete(key)

class HSCache:
    """HSキャッシュマネージャー"""
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
    
    def get(self, cache_key: str) -> Optional[Dict]:
        return self.backend.get(cache_key)
    
    def set(self, cache_key: str, result: Dict, ttl: int = 3600):
        self.backend.set(cache_key, result, ttl)
    
    def invalidate_by_rules_version(self, rules_version: str):
        """ルールバージョン変更時にキャッシュを無効化"""
        logger.info(f"Invalidating cache for rules version: {rules_version}")
        self.backend.clear()
```

---

## テスト計画

### ユニットテスト

```python
# backend/tests/test_hs_classifier.py

import pytest
from app.rules.engine import RuleEngine
from app.classify.scorer import HSScorer

def test_rule_engine_contains_any_ids():
    """contains_any_ids述語のテスト"""
    engine = RuleEngine()
    ingredients = [
        {"id": "ing_wheat_flour", "pct": 30.0},
        {"id": "ing_sugar", "pct": 25.0}
    ]
    assert engine._contains_any_ids(ingredients, ["ing_wheat_flour"]) == True
    assert engine._contains_any_ids(ingredients, ["ing_cocoa"]) == False

def test_rule_validation():
    """ルール検証のテスト"""
    # 不正なHSコードを持つルールでエラー
    with pytest.raises(RuleValidationError):
        engine = RuleEngine()
        engine.rules = [{"id": "test", "hs_code": "INVALID"}]
        engine.validate_rules()

def test_confidence_calculation():
    """信頼度計算のテスト (改善版)"""
    scorer = HSScorer()
    rule_matches = [
        {"weight": 0.8, "rule_id": "hs_food_001"},
        {"weight": 0.6, "rule_id": "hs_food_002"}
    ]
    product_data = {
        "ingredients": [{"id": "ing_wheat_flour", "pct": 35.0}]
    }
    confidence = scorer.calculate_confidence(rule_matches, product_data)
    assert 0.0 <= confidence <= 1.0
    assert confidence >= 0.6  # 閾値を上げたので0.6以上

def test_should_review_by_rule():
    """ルールベースのレビュー判定テスト"""
    scorer = HSScorer()
    top_candidate = {"confidence": 0.85, "code": "1905.90"}
    rule_matches = [{"requires_review": True, "rule_id": "test"}]
    
    assert scorer.should_review(top_candidate, rule_matches) == True

def test_should_review_by_hs_code():
    """HSコード範囲ベースのレビュー判定テスト"""
    scorer = HSScorer()
    top_candidate = {"confidence": 0.85, "code": "2106.90"}
    rule_matches = []
    
    assert scorer.should_review(top_candidate, rule_matches) == True
```

### 統合テスト

```python
def test_classify_chocolate_cookies(client):
    """チョコレートクッキーの分類テスト (OpenAPI準拠)"""
    resp = client.post("/v1/classify/hs", json={
        "product": {
            "name": "Chocolate cookies",
            "category": "confectionery",
            "origin_country": "JP",
            "ingredients": [
                {"id": "ing_wheat_flour", "pct": 30.0},
                {"id": "ing_sugar", "pct": 25.0},
                {"id": "ing_cocoa", "pct": 15.0}
            ],
            "process": ["baking"]
        },
        "traceId": "TEST-001"
    })
    
    assert resp.status_code == 200
    data = resp.get_json()
    
    # OpenAPI準拠のレスポンス検証
    assert "hs_candidates" in data
    assert "final_hs_code" in data
    assert "duty_rate" in data
    assert "risk_flags" in data
    assert "review_required" in data
    assert "explanations" in data
    assert "metadata" in data
    
    assert len(data["hs_candidates"]) > 0
    assert data["final_hs_code"] in ["1905.90", "1806.90"]
```

### E2Eテスト

```python
def test_e2e_classification_flow():
    """E2E分類フローのテスト (代表50品目)"""
    test_products = load_test_products("tests/data/products_50.json")
    
    correct = 0
    for product in test_products:
        result = classify_hs(product)
        if result["final_hs_code"] == product["expected_hs_code"]:
            correct += 1
    
    recall = correct / len(test_products)
    assert recall >= 0.80  # 80%以上のリコール
```

### 境界条件テスト

```python
def test_empty_ingredients(client):
    """成分なしのケース"""
    resp = client.post("/v1/classify/hs", json={
        "product": {
            "name": "Test product",
            "category": "confectionery",
            "ingredients": []
        }
    })
    # 信頼度が下がることを確認
    data = resp.get_json()
    assert data["hs_candidates"][0]["confidence"] < 0.7

def test_invalid_country_code(client):
    """無効な国コード"""
    resp = client.post("/v1/classify/hs", json={
        "product": {
            "name": "Test product",
            "origin_country": "XYZ"  # 無効
        }
    })
    assert resp.status_code == 422
    data = resp.get_json()
    assert "violations" in data
```

### 性能テスト

```python
def test_performance_p95():
    """P95 ≤ 300ms の検証"""
    import time
    
    test_products = load_test_products("tests/data/products_50.json")
    times = []
    
    for _ in range(20):  # 50品目 × 20回 = 1000リクエスト
        for product in test_products:
            start = time.time()
            classify_hs(product)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
    
    times.sort()
    p95_index = int(len(times) * 0.95)
    p95_time = times[p95_index]
    
    assert p95_time <= 300  # P95 ≤ 300ms
```

### ルール回帰テスト

```python
def test_rule_regression():
    """ルール変更時の回帰テスト (スナップショット)"""
    test_products = load_test_products("tests/data/products_50.json")
    snapshot = load_snapshot("tests/snapshots/hs_classification.json")
    
    for product in test_products:
        result = classify_hs(product)
        expected = snapshot[product["id"]]
        
        # HSコードが変わっていないことを確認
        assert result["final_hs_code"] == expected["final_hs_code"], \
            f"Regression detected for {product['id']}: " \
            f"expected {expected['final_hs_code']}, got {result['final_hs_code']}"
```

---

## 実装タスク

### Phase 1: ルールエンジン (2日)
- [ ] ルールDSL設計 (既存仕様準拠)
- [ ] 述語実装 (contains_any_ids, ingredient_pct_threshold等)
- [ ] YAMLローダー + バリデーション
- [ ] ルール評価エンジン
- [ ] ユニットテスト

### Phase 2: スコアリング (1日)
- [ ] 信頼度計算アルゴリズム (改善版)
- [ ] 候補ランキング (raw_confidence保持)
- [ ] レビュー判定ロジック (ビジネスルール考慮)
- [ ] ユニットテスト

### Phase 3: API実装 (2日)
- [ ] エンドポイント実装 (OpenAPI準拠)
- [ ] 入力バリデーション (既存エラー形式)
- [ ] エラーハンドリング (共通エラーラッパ)
- [ ] レスポンス生成 (duty_rate, risk_flags等)
- [ ] 統合テスト

### Phase 4: 説明可能性 (1日)
- [ ] Explainer実装 (i18n対応)
- [ ] Rationaleジェネレーター
- [ ] Explanationsフィールド (template_key + params)
- [ ] テスト

### Phase 5: データモデル・マイグレーション (0.5日)
- [ ] HSClassificationモデル実装
- [ ] マイグレーションファイル作成
- [ ] マイグレーション実行・検証

### Phase 6: キャッシュ・最適化 (1日)
- [ ] キャッシュ実装 (InMemory + Redis対応)
- [ ] キャッシュキー生成 (ルールバージョン含む)
- [ ] パフォーマンステスト
- [ ] P95 ≤ 300ms達成

### Phase 7: E2Eテスト・回帰テスト (1.5日)
- [ ] 代表50品目テスト
- [ ] リコール≥80%達成
- [ ] ルール回帰テスト (スナップショット)
- [ ] 境界条件テスト
- [ ] ドキュメント更新

**総見積**: 8-9日

---

## 次のステップ

### 実装前の確認事項

1. **既存OpenAPIとの最終確認**
   - [ ] リクエスト/レスポンス形式の完全一致
   - [ ] エラー形式の統一

2. **ルールファイルの準備**
   - [ ] `rules/hs_food.yml` の作成
   - [ ] 代表50品目の期待値定義

3. **成分IDマスタの準備**
   - [ ] canonical ingredient ID リストの作成
   - [ ] 翻訳API との連携確認

### 実装順序 (推奨)

1. **Phase 1**: ルールエンジン (基盤)
2. **Phase 2**: スコアリング (ロジック)
3. **Phase 5**: データモデル (DB準備)
4. **Phase 3**: API実装 (エンドポイント)
5. **Phase 4**: 説明可能性 (付加価値)
6. **Phase 6**: キャッシュ (最適化)
7. **Phase 7**: E2Eテスト (検証)

---

## 関連ドキュメント

- [OpenAPI仕様](file:///d:/works2025/越境EC/crossover_win/crossborder/backend/openapi.yaml)
- [全体仕様書](file:///d:/works2025/越境EC/crossover_win/crossborder/docs/SPEC.md)
- [機能一覧](file:///d:/works2025/越境EC/crossover_win/crossborder/docs/機能一覧.md)

---

最終更新: 2025-12-05 (v2.0)
