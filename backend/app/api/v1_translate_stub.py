from flask import Blueprint, jsonify

bp = Blueprint("translate", __name__)


@bp.post("/translate/ingredients")
def translate_ingredients():
    return jsonify(
        {
            "ingredients_line": "Ingredients: wheat flour, sugar, egg.",
            "contains_line": "Contains: Egg, Wheat.",
            "confidence": 0.99,
            "warnings": [],
        }
    )
