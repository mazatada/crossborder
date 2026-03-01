import json
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, jsonify, request, Response
from app.auth import require_api_key
from app.rules.engine import RuleEngine, RuleValidationError, RuleValidator
from app.audit import log_event

bp = Blueprint("v1_hs_rules", __name__, url_prefix="/v1")

_RULES_CACHE: Dict[str, Dict[str, Any]] = {}
_RULES_LOADED = False
_RULES_LOAD_ERROR: Optional[str] = None


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _error_400(
    message: str, field: str, error_class: str = "invalid_argument"
) -> Tuple[Response, int]:
    return (
        jsonify(
            {
                "error": {
                    "class": error_class,
                    "message": message,
                    "field": field,
                    "severity": "block",
                }
            }
        ),
        400,
    )


def _error_404(message: str = "not found", field: str = "id") -> Tuple[Response, int]:
    return (
        jsonify(
            {
                "error": {
                    "class": "not_found",
                    "message": message,
                    "field": field,
                    "severity": "block",
                }
            }
        ),
        404,
    )


def _error_rule_dsl(
    message: str,
    expression: str,
    field: str,
    details: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    payload: Dict[str, Any] = {
        "class": "rule_dsl_error",
        "message": message,
        "field": field,
        "severity": "block",
        "details": {
            "expression": expression,
            "hint": "Provide JSON conditions compatible with RuleEngine predicates",
        },
    }
    if details:
        payload["details"].update(details)
    return jsonify({"error": payload}), 400


def _error_500(message: str) -> Tuple[Response, int]:
    return jsonify({"error": {"class": "internal", "message": message}}), 500


def _trace_id(data: Optional[Dict[str, Any]] = None) -> Optional[str]:
    if data and data.get("trace_id"):
        return data.get("trace_id")
    return request.headers.get("X-Trace-ID")


def _parse_and_validate_conditions(
    condition_dsl: str,
    field: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Response, int]]]:
    try:
        conditions = json.loads(condition_dsl)
    except json.JSONDecodeError as e:
        return None, _error_rule_dsl(
            "Invalid DSL format (expected JSON conditions)",
            condition_dsl,
            field,
            {"line": e.lineno, "column": e.colno},
        )

    try:
        RuleValidator().validate_conditions(conditions)
    except RuleValidationError as e:
        return None, _error_rule_dsl(str(e), condition_dsl, field)

    return conditions, None


def _load_rules() -> None:
    global _RULES_LOADED
    global _RULES_LOAD_ERROR
    if _RULES_LOADED:
        return
    try:
        engine = RuleEngine()
        for rule in engine.rules:
            rule_id = str(rule.get("id"))
            _RULES_CACHE[rule_id] = {
                "id": rule_id,
                "name": rule.get("name"),
                "description": rule.get("description"),
                "priority": rule.get("priority", 0),
                "scope": rule.get("scope"),
                "condition_dsl": json.dumps(
                    rule.get("conditions", {}), ensure_ascii=False
                ),
                "effect": {
                    "hs_code": rule.get("hs_code"),
                    "weight": rule.get("weight", 1.0),
                    "tags": rule.get("tags", []),
                },
                "status": rule.get("status", "active"),
                "version": rule.get("version", 1),
                "created_by": None,
                "updated_by": None,
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            }
        _RULES_LOADED = True
    except RuleValidationError as e:
        _RULES_LOADED = True
        _RULES_LOAD_ERROR = str(e)
    except Exception as e:
        _RULES_LOADED = True
        _RULES_LOAD_ERROR = str(e)


def _ensure_rules_loaded() -> Optional[Tuple[Response, int]]:
    _load_rules()
    if _RULES_LOAD_ERROR:
        return _error_500("Rule engine initialization failed")
    return None


def _get_rule(rule_id: str) -> Optional[Dict[str, Any]]:
    _load_rules()
    return _RULES_CACHE.get(rule_id)


@bp.get("/hs-rules")
@require_api_key
def list_hs_rules() -> Tuple[Response, int]:
    error = _ensure_rules_loaded()
    if error:
        return error
    status = request.args.get("status")
    scope = request.args.get("scope")
    limit = int(request.args.get("limit", "20"))
    cursor = request.args.get("cursor")
    offset = int(cursor) if cursor and cursor.isdigit() else 0

    rules = list(_RULES_CACHE.values())
    if status:
        rules = [r for r in rules if r.get("status") == status]
    if scope:
        rules = [r for r in rules if r.get("scope") == scope]

    sliced = rules[offset : offset + limit]
    next_offset = offset + len(sliced)
    has_more = next_offset < len(rules)
    next_cursor = str(next_offset) if has_more else None

    return (
        jsonify({"items": sliced, "has_more": has_more, "next_cursor": next_cursor}),
        200,
    )


@bp.post("/hs-rules")
@require_api_key
def create_hs_rule() -> Tuple[Response, int]:
    error = _ensure_rules_loaded()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    condition_dsl = data.get("condition_dsl")
    effect = data.get("effect", {})
    if not name:
        return _error_400("name is required", "name", "missing_required")
    if not condition_dsl:
        return _error_400(
            "condition_dsl is required", "condition_dsl", "missing_required"
        )
    if not effect or not effect.get("hs_code"):
        return _error_400(
            "effect.hs_code is required", "effect.hs_code", "missing_required"
        )
    _, error = _parse_and_validate_conditions(condition_dsl, "condition_dsl")
    if error:
        return error

    rule_id = data.get("id") or f"rule_{uuid.uuid4().hex[:10]}"
    rule = {
        "id": rule_id,
        "name": name,
        "description": data.get("description"),
        "priority": data.get("priority", 0),
        "scope": data.get("scope"),
        "condition_dsl": condition_dsl,
        "effect": effect,
        "status": data.get("status", "draft"),
        "version": 1,
        "created_by": data.get("created_by"),
        "updated_by": data.get("updated_by"),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _RULES_CACHE[rule_id] = rule
    log_event(
        trace_id=_trace_id(data),
        event="hs.rule.create",
        target_type="hs_rule",
        target_id=None,
        rule_id=rule_id,
    )
    return jsonify(rule), 201


@bp.get("/hs-rules/<id>")
@require_api_key
def get_hs_rule(id: str) -> Tuple[Response, int]:
    error = _ensure_rules_loaded()
    if error:
        return error
    rule = _get_rule(id)
    if not rule:
        return _error_404()
    return jsonify(rule), 200


@bp.put("/hs-rules/<id>")
@require_api_key
def update_hs_rule(id: str) -> Tuple[Response, int]:
    error = _ensure_rules_loaded()
    if error:
        return error
    rule = _get_rule(id)
    if not rule:
        return _error_404()

    data = request.get_json(silent=True) or {}
    version_bump_fields = {"condition_dsl", "effect", "priority", "scope"}

    if "condition_dsl" in data:
        if not data.get("condition_dsl"):
            return _error_400(
                "condition_dsl is required", "condition_dsl", "missing_required"
            )
        _, error = _parse_and_validate_conditions(
            data.get("condition_dsl") or "", "condition_dsl"
        )
        if error:
            return error

    bump = any(field in data for field in version_bump_fields)
    for field in [
        "name",
        "description",
        "priority",
        "scope",
        "condition_dsl",
        "effect",
        "status",
    ]:
        if field in data:
            rule[field] = data.get(field)
    rule["updated_by"] = data.get("updated_by") or rule.get("updated_by")
    rule["updated_at"] = _now_iso()
    if bump:
        rule["version"] = int(rule.get("version", 1)) + 1

    log_event(
        trace_id=_trace_id(data),
        event="hs.rule.update",
        target_type="hs_rule",
        target_id=None,
        rule_id=id,
    )
    return jsonify(rule), 200


@bp.delete("/hs-rules/<id>")
@require_api_key
def delete_hs_rule(id: str) -> Tuple[Response, int]:
    error = _ensure_rules_loaded()
    if error:
        return error
    rule = _get_rule(id)
    if not rule:
        return _error_404()
    rule["status"] = "inactive"
    rule["updated_at"] = _now_iso()
    log_event(
        trace_id=_trace_id(),
        event="hs.rule.delete",
        target_type="hs_rule",
        target_id=None,
        rule_id=id,
    )
    return Response(status=204), 204


@bp.post("/hs-rules:test")
@require_api_key
def test_hs_rule() -> Tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    rule = data.get("rule") or {}
    product_sample = data.get("product_sample") or {}

    condition_dsl = rule.get("condition_dsl")
    effect = rule.get("effect", {})
    if not condition_dsl:
        return _error_400(
            "condition_dsl is required", "rule.condition_dsl", "missing_required"
        )

    conditions, error = _parse_and_validate_conditions(
        condition_dsl, "rule.condition_dsl"
    )
    if error:
        return error

    try:
        engine = RuleEngine()
    except RuleValidationError:
        return _error_500("Rule engine initialization failed")
    rule_obj = {
        "id": rule.get("id", "test"),
        "name": rule.get("name", "test"),
        "hs_code": effect.get("hs_code"),
        "weight": effect.get("weight", 1.0),
        "priority": rule.get("priority", 0),
        "conditions": conditions,
    }

    try:
        matched = engine._evaluate_rule(rule_obj, product_sample)
    except Exception as e:
        return _error_rule_dsl(
            str(e),
            condition_dsl,
            "rule.condition_dsl",
            {"hint": "Check predicate names and arguments"},
        )

    return (
        jsonify(
            {
                "matched": bool(matched),
                "reason": [],
                "effect_preview": effect if matched else None,
            }
        ),
        200,
    )
