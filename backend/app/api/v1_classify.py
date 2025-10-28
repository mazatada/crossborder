from flask import Blueprint, request, jsonify

bp = Blueprint("v1_classify", __name__, url_prefix="/v1")

@bp.post("/classify/hs")
def classify_hs():
    data = request.get_json(silent=True) or {}
    product = data.get("product") or {}
    if not isinstance(product, dict):
        return jsonify({"status":"error","error":{"code":"INVALID_ARGUMENT","message":"product は必須"}}), 400

    ingredients = product.get("ingredients") or []
    if not isinstance(ingredients, list) or len(ingredients) == 0:
        return jsonify({"status":"error","error":{"code":"UNPROCESSABLE","message":"ingredients が空です"}}), 422

    # モック応答
    return jsonify({
        "hs_candidates": [
            {"code": "1905.90", "confidence": 0.82, "rationale": ["wheat flour present", "baked product"]}
        ],
        "required_uom": "kg",
        "review_required": False,
        "risk_flags": []
    }), 200
