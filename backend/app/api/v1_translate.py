import os
import json
from flask import Blueprint, request, jsonify
from app.audit import record_event

bp = Blueprint("v1_translate", __name__, url_prefix="/v1")

@bp.post("/translate/ingredients")
def translate_ingredients():
    data = request.get_json(silent=True) or {}
    text = data.get("text_ja")
    image_id = data.get("image_media_id")
    trace_id = data.get("traceId")

    # どちらか必須
    if not ((isinstance(text, str) and text.strip()) or (isinstance(image_id, str) and image_id.strip())):
        return jsonify({
            "status": "error",
            "error": {"code": "INVALID_ARGUMENT", "message": "text_ja または image_media_id のいずれか必須"}
        }), 400

    # OpenAI API Key check
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Mock response if no key or explicitly requested (for testing)
    if not api_key or text == "MOCK_TEST":
        terms = [
            {"ja": "小麦粉", "en": "wheat flour", "canonical_id": "ing_wheat_flour", "confidence": 0.92},
            {"ja": "砂糖",   "en": "sugar",        "canonical_id": "ing_sugar",       "confidence": 0.95},
            {"ja": "卵",     "en": "egg",          "canonical_id": "ing_egg",         "confidence": 0.90},
        ]
        if trace_id:
            record_event(event="TRANSLATE_MOCK", trace_id=trace_id, text_len=len(text) if text else 0)
        return jsonify({"terms": terms, "glossary_hits": []}), 200

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        Translate the following Japanese food ingredients to English.
        Return a JSON object with a key "terms" which is a list of objects.
        Each object must have: "ja" (original), "en" (translation), "confidence" (0.0-1.0).
        Canonical IDs are optional.
        
        Input: {text}
        """
        
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful translator for food ingredients. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        content = completion.choices[0].message.content
        result = json.loads(content)
        terms = result.get("terms", [])
        
        if trace_id:
            record_event(event="TRANSLATE_LLM", trace_id=trace_id, model="gpt-3.5-turbo", count=len(terms))
            
        return jsonify({"terms": terms, "glossary_hits": []}), 200

    except Exception as e:
        if trace_id:
            record_event(event="TRANSLATE_ERROR", trace_id=trace_id, error=str(e))
        return jsonify({
            "status": "error", 
            "error": {"code": "INTERNAL", "message": str(e)}
        }), 500
