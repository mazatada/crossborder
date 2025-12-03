import re
from flask import Blueprint, request, jsonify
from app.audit import record_event

bp = Blueprint("v1_classify", __name__, url_prefix="/v1")

# Simple Rule Engine (In-memory)
RULES = [
    {"code": "1905.90", "keywords": ["cookie", "biscuit", "cake", "bread"], "rationale": "Baked goods"},
    {"code": "2106.90", "keywords": ["supplement", "vitamin", "powder"], "rationale": "Food preparations/supplements"},
    {"code": "0902.10", "keywords": ["tea", "green tea"], "rationale": "Green tea"},
    {"code": "1806.32", "keywords": ["chocolate"], "rationale": "Chocolate products"},
]

@bp.post("/classify/hs")
def classify_hs():
    data = request.get_json(silent=True) or {}
    product = data.get("product") or {}
    trace_id = data.get("traceId")

    if not isinstance(product, dict):
        return jsonify({"status":"error","error":{"code":"INVALID_ARGUMENT","message":"product は必須"}}), 400

    ingredients = product.get("ingredients") or []
    product_name = product.get("name", "").lower()
    
    if not isinstance(ingredients, list) or len(ingredients) == 0:
        return jsonify({"status":"error","error":{"code":"UNPROCESSABLE","message":"ingredients が空です"}}), 422

    # Rule Matching Logic
    candidates = []
    
    # Check Product Name
    for rule in RULES:
        for kw in rule["keywords"]:
            if kw in product_name:
                candidates.append({
                    "code": rule["code"],
                    "confidence": 0.85,
                    "rationale": [f"Product name matches '{kw}' ({rule['rationale']})"]
                })

    # Check Ingredients (if no match yet or to boost confidence)
    # Normalize ingredients: support both string and dict formats
    normalized_ingredients = []
    for i in ingredients:
        if isinstance(i, str):
            normalized_ingredients.append(i)
        elif isinstance(i, dict):
            normalized_ingredients.append(i.get("en", ""))
    ing_text = " ".join(normalized_ingredients).lower()
    for rule in RULES:
        for kw in rule["keywords"]:
            if kw in ing_text:
                # Check if already added
                existing = next((c for c in candidates if c["code"] == rule["code"]), None)
                if existing:
                    existing["confidence"] = min(0.99, existing["confidence"] + 0.1)
                    existing["rationale"].append(f"Ingredient matches '{kw}'")
                else:
                    candidates.append({
                        "code": rule["code"],
                        "confidence": 0.6,
                        "rationale": [f"Ingredient matches '{kw}' ({rule['rationale']})"]
                    })

    # Sort by confidence
    candidates.sort(key=lambda x: x["confidence"], reverse=True)

    # Fallback if empty
    if not candidates:
        candidates.append({
            "code": "0000.00", 
            "confidence": 0.0, 
            "rationale": ["No rules matched. Manual review required."]
        })

    result = {
        "hs_candidates": candidates,
        "required_uom": "kg", # Simplified
        "review_required": candidates[0]["confidence"] < 0.7,
        "risk_flags": []
    }

    if trace_id:
        record_event(event="CLASSIFY_HS", trace_id=trace_id, 
            top_code=candidates[0]["code"], 
            confidence=candidates[0]["confidence"]
        )

    return jsonify(result), 200
