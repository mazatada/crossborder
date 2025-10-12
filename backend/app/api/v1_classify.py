from flask import Blueprint, request, jsonify
import yaml, os
from ..util.validate import require_json
bp = Blueprint("classify", __name__)

RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules", "hs_food.yml")
with open(RULES_PATH, "r", encoding="utf-8") as f:
    HS_RULES = (yaml.safe_load(f) or [])

def eval_pred(p, expr, ctx):
    if "all" in expr: return all(eval_pred(p, e, ctx) for e in expr["all"])
    if "any" in expr: return any(eval_pred(p, e, ctx) for e in expr["any"])
    if "contains_any" in expr:
        ids = set([x.get("id") for x in p.get("ingredients",[])])
        return any(i in ids for i in expr["contains_any"]["ingredient_ids"])
    if "process_any" in expr:
        return any(x in (p.get("process") or []) for x in expr["process_any"])
    if "category_is" in expr:
        return (p.get("category") or "") in expr["category_is"]
    if "product_name_matches" in expr:
        import re
        return re.search(expr["product_name_matches"], p.get("name","") or "", re.I) is not None
    if "last_hit_in" in expr:
        return ctx.get("last_hit") in expr["last_hit_in"]
    if "sugar_ratio_gte" in expr:
        n = p.get("nutrition") or {}
        denom = sum(n.get(k,0.0) for k in ["fat_g","protein_g","carb_g"])
        return denom and (n.get("sugar_g",0.0)/denom) >= expr["sugar_ratio_gte"]
    if "cocoa_ratio_gte" in expr:
        # MVP: presence proxy only
        return any(i.get("id") in ["ing_cocoa_powder","ing_cocoa_mass","ing_chocolate"] for i in p.get("ingredients",[]))
    return False

@bp.post("/classify/hs")
@require_json
def classify_hs():
    payload = request.get_json()
    product = payload.get("product",{})
    ctx = {"last_hit": None}
    hints, rationale = set(), []
    for r in HS_RULES:
        w, t = r.get("when"), r.get("then")
        if not w or not t: continue
        if eval_pred(product, w, ctx):
            ctx["last_hit"] = r["id"]
            for h in t.get("heading_hints",[]): hints.add(h)
            if "rationale" in t: rationale += t["rationale"]
    # MVP scoring: simple heuristic toward hinted headings
    candidates = []
    if "1905.90" in hints:
        candidates.append({"code":"1905.90","confidence":0.82,"rationale":rationale+["rule hits: 1905.90"],"required_uom":"kg"})
    if "2106.90" in hints:
        candidates.append({"code":"2106.90","confidence":0.14,"rationale":["miscellaneous"]})
    if not candidates:
        candidates.append({"code":"2106.90","confidence":0.5,"rationale":["fallback"]})
    resp = {
        "hs_candidates": candidates[:3],
        "duty_rate": {"ad_valorem_pct": 4.0, "additional":[]},
        "risk_flags": {"ad_cvd": False, "import_alert": False},
        "quota_applicability": "unknown",
        "review_required": False
    }
    return jsonify(resp), 200
