from typing import Any, Dict, Optional
from flask import jsonify
from werkzeug.exceptions import HTTPException


def error_response(
    *,
    status: int,
    err_class: str,
    message: str,
    code: str,
    fields: Optional[Dict[str, Any]] = None
):
    payload: Dict[str, Any] = {
        "error": {"class": err_class, "message": message, "code": code}
    }
    if fields:
        payload["error"]["fields"] = fields
    resp = jsonify(payload)
    resp.status_code = status
    return resp


# Flask標準のHTTP例外をJSONで返す
def _handle_http_exception(e: HTTPException):
    return error_response(
        status=e.code or 500,
        err_class=e.name or "HTTPException",
        message=e.description or "HTTP error",
        code=(e.name or "HTTP_ERROR").upper().replace(" ", "_"),
    )


# 予期せぬ例外もJSONに統一（開発時はログに出る）
def _handle_generic_exception(e: Exception):
    return error_response(
        status=500,
        err_class=e.__class__.__name__,
        message="internal server error",
        code="INTERNAL_ERROR",
    )


def register_error_handlers(app):
    # 全HTTP例外
    app.register_error_handler(HTTPException, _handle_http_exception)
    # その他例外
    app.register_error_handler(Exception, _handle_generic_exception)
