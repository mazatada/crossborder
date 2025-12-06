"""
HS分類API - v1エンドポイント

商品情報からHSコードを自動分類するAPIエンドポイント
"""

from typing import Tuple
from flask import Blueprint, request, jsonify, Response
from app.auth import require_api_key
from app.audit import log_event
from app.classify import HSClassifier, ClassificationError
from app.models import HSClassification
from app.db import db
import time
import uuid
import logging

logger = logging.getLogger(__name__)

bp = Blueprint("v1_classify", __name__, url_prefix="/v1")


@bp.route("/classify/hs", methods=["POST"])
@require_api_key
def classify_hs() -> Tuple[Response, int]:
    """
    HS分類API
    
    商品情報からHSコードを自動分類し、信頼度スコアと判断根拠を返す。
    """
    start_time = time.time()
    
    # トレースID取得/生成
    trace_id = request.headers.get("X-Trace-ID") or request.json.get("traceId") or f"hs-{uuid.uuid4().hex[:16]}"
    
    try:
        # リクエストボディ取得
        data = request.json
        if not data:
            return jsonify({
                "error": {
                    "class": "missing_required",
                    "message": "Request body is required",
                    "field": "body",
                    "severity": "block"
                }
            }), 400
        
        # product オブジェクト取得
        product = data.get("product")
        if not product:
            return jsonify({
                "error": {
                    "class": "missing_required",
                    "message": "product is required",
                    "field": "product",
                    "severity": "block"
                }
            }), 400
        
        # 必須フィールドチェック
        if not product.get("name"):
            return jsonify({
                "error": {
                    "class": "missing_required",
                    "message": "product.name is required",
                    "field": "product.name",
                    "severity": "block"
                }
            }), 400
        
        # バリデーション
        violations = []
        
        # 国コード検証 (ISO 3166-1 alpha-2)
        origin_country = product.get("origin_country")
        if origin_country and len(origin_country) != 2:
            violations.append({
                "field": "product.origin_country",
                "rule": "iso_3166_1_alpha_2",
                "message": f"Invalid country code: '{origin_country}'. Must be ISO 3166-1 alpha-2 format (2 characters)."
            })
        
        # ingredients型チェック
        ingredients = product.get("ingredients")
        if ingredients is not None and not isinstance(ingredients, list):
            violations.append({
                "field": "product.ingredients",
                "rule": "type_check",
                "message": "ingredients must be an array"
            })
        
        # process型チェック
        process = product.get("process")
        if process is not None and not isinstance(process, list):
            violations.append({
                "field": "product.process",
                "rule": "type_check",
                "message": "process must be an array"
            })
        
        if violations:
            logger.warning(f"Validation failed: trace_id={trace_id}, violations={violations}")
            return jsonify({"violations": violations}), 422
        
        # 監査ログ: リクエスト受信
        log_event(
            trace_id=trace_id,
            event="hs_classification_requested",
            product_name=product.get("name"),
            category=product.get("category"),
            origin_country=origin_country
        )
        
        # HS分類実行
        classifier = HSClassifier()
        try:
            result = classifier.classify(product)
        except ClassificationError as e:
            # 分類失敗
            log_event(
                trace_id=trace_id,
                event="hs_classification_failed",
                error=str(e),
                product_name=product.get("name")
            )
            
            return jsonify({
                "violations": [{
                    "field": "classification",
                    "rule": "min_confidence",
                    "message": str(e)
                }]
            }), 422
        
        # 処理時間計測
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # レスポンス生成 (OpenAPI準拠)
        response = {
            "hs_candidates": result["hs_candidates"],
            "final_hs_code": result["final_hs_code"],
            "duty_rate": {
                "ad_valorem_pct": None,
                "additional": []
            },
            "risk_flags": {
                "ad_cvd": False,
                "import_alert": False
            },
            "quota_applicability": None,
            "review_required": result["review_required"],
            "explanations": result.get("explanations", []),
            "metadata": {
                "classification_method": "rule_based",
                "processing_time_ms": processing_time_ms,
                "cache_hit": result.get("cache_hit", False),
                "rules_version": classifier.get_rules_version()
            }
        }
        
        # DB保存
        try:
            hs_classification = HSClassification(
                product_id=data.get("product_id"),
                trace_id=trace_id,
                product_name=product.get("name"),
                category=product.get("category"),
                origin_country=origin_country,
                ingredients=ingredients,
                process=process,
                hs_candidates=result["hs_candidates"],
                final_hs_code=result["final_hs_code"],
                required_uom=result["required_uom"],
                review_required=result["review_required"],
                duty_rate=response["duty_rate"],
                risk_flags=response["risk_flags"],
                quota_applicability=response["quota_applicability"],
                explanations=response["explanations"],
                classification_method="rule_based",
                processing_time_ms=processing_time_ms,
                cache_hit=result.get("cache_hit", False),
                rules_version=classifier.get_rules_version()
            )
            db.session.add(hs_classification)
            db.session.commit()
            
            logger.info(f"HS classification saved: id={hs_classification.id}, trace_id={trace_id}")
        except Exception as e:
            logger.error(f"Failed to save HS classification: {e}")
            db.session.rollback()
            # DB保存失敗してもレスポンスは返す
        
        # 監査ログ: 分類成功
        log_event(
            trace_id=trace_id,
            event="hs_classification_completed",
            final_hs_code=result["final_hs_code"],
            review_required=result["review_required"],
            processing_time_ms=processing_time_ms
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in classify_hs: {e}", exc_info=True)
        log_event(trace_id=trace_id, event="hs_classification_error", error=str(e))
        
        return jsonify({
            "error": {
                "class": "internal_error",
                "message": "An unexpected error occurred",
                "severity": "block"
            }
        }), 500
