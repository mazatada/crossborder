from flask import Blueprint, request, jsonify

bp = Blueprint("v1_translate", __name__, url_prefix="/v1")

@bp.post("/translate/ingredients")
def translate_ingredients():
    data = request.get_json(silent=True) or {}
    text = data.get("text_ja")
    image_id = data.get("image_media_id")

    # どちらか必須
    if not ((isinstance(text, str) and text.strip()) or (isinstance(image_id, str) and image_id.strip())):
        return jsonify({
            "status": "error",
            "error": {"code": "INVALID_ARGUMENT", "message": "text_ja または image_media_id のいずれか必須"}
        }), 400

    # モック応答（固定）
    terms = [
        {"ja": "小麦粉", "en": "wheat flour", "canonical_id": "ing_wheat_flour", "confidence": 0.92},
        {"ja": "砂糖",   "en": "sugar",        "canonical_id": "ing_sugar",       "confidence": 0.95},
        {"ja": "卵",     "en": "egg",          "canonical_id": "ing_egg",         "confidence": 0.90},
    ]
    return jsonify({"terms": terms, "glossary_hits": []}), 200
