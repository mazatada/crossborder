from typing import Dict, Any, Optional, Tuple
from flask import Blueprint, request, jsonify, Response
import re
import os
import json
import logging
import time
from app.auth import require_api_key

bp = Blueprint("v1_tariffs", __name__, url_prefix="/v1")

DEFAULT_TARIFFS: Dict[Tuple[str, str], Dict[str, Any]] = {
    ("US", "190590"): {
        "ad_valorem_rate": 0.05,
        "currency": "USD",
        "basis_uom": None,
        "tariff_schedule_version": "HTSUS_2025_v3",
        "last_updated_at": "2025-11-20T00:00:00Z",
        "additional_duties": [],
    }
}

_TARIFFS_CACHE: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None
_TARIFF_SOURCE: str = "internal_master"
_TARIFFS_LOADED_AT: Optional[float] = None
_TARIFFS_TTL_SECONDS = int(os.getenv("TARIFFS_TTL_SECONDS", "300"))

logger = logging.getLogger(__name__)


def _load_tariffs() -> Dict[Tuple[str, str], Dict[str, Any]]:
    global _TARIFFS_CACHE, _TARIFF_SOURCE
    global _TARIFFS_LOADED_AT
    if _TARIFFS_CACHE is not None and _TARIFFS_LOADED_AT is not None:
        if (time.time() - _TARIFFS_LOADED_AT) < _TARIFFS_TTL_SECONDS:
            return _TARIFFS_CACHE

    def _validate_item(item: Dict[str, Any]) -> Optional[str]:
        required = [
            "destination_country",
            "hs_code",
            "ad_valorem_rate",
            "tariff_schedule_version",
            "last_updated_at",
        ]
        for k in required:
            if k not in item:
                return f"missing {k}"
        if len(item["destination_country"]) != 2:
            return "invalid destination_country"
        if not re.match(r"^\d{4}(\.\d{2}){0,2}$|^\d{6,10}$", item["hs_code"]):
            return "invalid hs_code"
        return None
        return _TARIFFS_CACHE

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    default_path = os.path.join(base_dir, "data", "tariffs.json")
    tariffs_path = os.getenv("TARIFFS_PATH", default_path)

    try:
        with open(tariffs_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
            items = payload.get("tariffs", [])
            source = payload.get("source", "internal_master")
            result: Dict[Tuple[str, str], Dict[str, Any]] = {}
            for t in items:
                err = _validate_item(t)
                if err:
                    logger.warning("tariff item skipped: %s (%s)", t, err)
                    continue
                key = (t["destination_country"].upper(), _normalize_hs_code(t["hs_code"]))
                result[key] = {
                    "ad_valorem_rate": t["ad_valorem_rate"],
                    "currency": t.get("currency", "USD"),
                    "basis_uom": t.get("basis_uom"),
                    "tariff_schedule_version": t.get("tariff_schedule_version", "unknown"),
                    "last_updated_at": t.get("last_updated_at"),
                    "additional_duties": t.get("additional_duties", []),
                }
            _TARIFFS_CACHE = result or DEFAULT_TARIFFS
            _TARIFF_SOURCE = source
            _TARIFFS_LOADED_AT = time.time()
            return _TARIFFS_CACHE
    except Exception:
        logger.exception("failed to load tariffs json, falling back to defaults")
        _TARIFFS_CACHE = DEFAULT_TARIFFS
        _TARIFF_SOURCE = "internal_master"
        _TARIFFS_LOADED_AT = time.time()
        return _TARIFFS_CACHE


def _normalize_hs_code(code: str) -> str:
    return code.replace(".", "").strip()


def _error_400(message: str, field: str) -> Tuple[Response, int]:
    return (
        jsonify(
            {
                "error": {
                    "class": "missing_required",
                    "message": message,
                    "field": field,
                    "severity": "block",
                }
            }
        ),
        400,
    )


def _get_tariff(
    destination_country: str, hs_code: str
) -> Optional[Dict[str, Any]]:
    key = (destination_country.upper(), _normalize_hs_code(hs_code))
    tariffs = _load_tariffs()
    return tariffs.get(key)


@bp.get("/tariffs/<destination_country>/<hs_code>")
@require_api_key
def get_tariff(destination_country: str, hs_code: str) -> Tuple[Response, int]:
    origin_country = request.args.get("origin_country")
    as_of = request.args.get("as_of")

    if not destination_country or len(destination_country) != 2:
        return _error_400("Invalid destination_country", "destination_country")
    if origin_country and len(origin_country) != 2:
        return _error_400("Invalid origin_country", "origin_country")
    if as_of and not re.match(r"^\\d{4}-\\d{2}-\\d{2}$", as_of):
        return _error_400("Invalid as_of format (YYYY-MM-DD)", "as_of")
    if not re.match(r"^\d{4}(\.\d{2}){0,2}$|^\d{6,10}$", hs_code):
        return _error_400("Invalid hs_code format", "hs_code")

    tariff = _get_tariff(destination_country, hs_code)
    if not tariff:
        return jsonify({"error": {"class": "not_found"}}), 404

    ad_valorem_rate = tariff["ad_valorem_rate"]
    response = {
        "destination_country": destination_country.upper(),
        "hs_code": hs_code,
        "origin_country": origin_country,
        "as_of": as_of,
        "duty_rate": {
            "type": "ad_valorem",
            "ad_valorem_rate": ad_valorem_rate,
            "ad_valorem_pct": ad_valorem_rate * 100,
            "specific": None,
            "currency": tariff["currency"],
            "basis_uom": tariff["basis_uom"],
        },
        "additional_duties": tariff["additional_duties"],
        "metadata": {
            "tariff_schedule_version": tariff["tariff_schedule_version"],
            "source": _TARIFF_SOURCE,
            "last_updated_at": tariff["last_updated_at"],
            "note": "origin_country/as_of are accepted; as_of is validated for format only (MVP).",
        },
    }
    return jsonify(response), 200


@bp.post("/tariffs/calculate")
@require_api_key
def calculate_tariff() -> Tuple[Response, int]:
    data = request.get_json(silent=True) or {}

    hs_code = data.get("hs_code")
    origin_country = data.get("origin_country")
    destination_country = data.get("destination_country")
    customs_value = data.get("customs_value")

    if not hs_code:
        return _error_400("hs_code is required", "hs_code")
    if not origin_country:
        return _error_400("origin_country is required", "origin_country")
    if not destination_country:
        return _error_400("destination_country is required", "destination_country")
    if not customs_value or "amount" not in customs_value:
        return _error_400("customs_value.amount is required", "customs_value.amount")
    if not re.match(r"^\d{4}(\.\d{2}){0,2}$|^\d{6,10}$", hs_code):
        return _error_400("Invalid hs_code format", "hs_code")

    tariff = _get_tariff(destination_country, hs_code)
    if not tariff:
        return jsonify({"error": {"class": "not_found"}}), 404

    ad_valorem_rate = tariff["ad_valorem_rate"]
    amount = float(customs_value["amount"])
    basic_amount = amount * ad_valorem_rate

    response = {
        "hs_code": hs_code,
        "origin_country": origin_country,
        "destination_country": destination_country.upper(),
        "customs_value": customs_value,
        "duty": {
            "total_amount": basic_amount,
            "currency": customs_value.get("currency", tariff["currency"]),
            "components": [
                {
                    "type": "basic",
                    "rate_type": "ad_valorem",
                    "rate": ad_valorem_rate,
                    "amount": basic_amount,
                    "basis": "customs_value",
                }
            ],
        },
        "applied_rates": {
            "tariff_schedule_version": tariff["tariff_schedule_version"],
            "rules": [
                {
                    "code": "basic",
                    "description": "MFN rate",
                    "legal_reference": f"{destination_country.upper()} {hs_code}",
                }
            ],
        },
    }
    return jsonify(response), 200
