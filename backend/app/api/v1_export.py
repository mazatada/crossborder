from flask import Blueprint, jsonify

bp = Blueprint("export", __name__)


@bp.get("/export/isf")
def export_isf():
    return jsonify(
        {"columns": ["manufacturer", "supplier", "ship_to", "hts6", "uom"], "rows": []}
    )


@bp.get("/export/entry")
def export_entry():
    return jsonify(
        {"columns": ["line_no", "hts6", "uom", "qty", "origin", "value"], "rows": []}
    )
