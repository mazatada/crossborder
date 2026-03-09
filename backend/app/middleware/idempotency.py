"""Idempotency middleware decorator for Flask API endpoints (Phase 4a).

Usage:
    @bp.post("/some-endpoint")
    @require_idempotency_key
    def create_something():
        ...

The decorator:
1. Reads the ``Idempotency-Key`` header from the request.
2. Attempts INSERT with ON CONFLICT DO NOTHING (UPSERT-like approach).
3. If the key already exists:
   - COMPLETED → returns cached response
   - IN_PROGRESS → returns 409 Conflict
   - FAILED → allows retry (deletes old record, inserts fresh one)
4. On successful view execution, stores the response in the record.
"""

from __future__ import annotations

import functools
import json
import logging
from typing import Optional

from flask import request, jsonify
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


def require_idempotency_key(f):  # type: ignore
    """Decorator that enforces idempotency via ``Idempotency-Key`` header."""

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):  # type: ignore
        from app.db import db
        from app.models import IdempotencyRecord

        idem_key: Optional[str] = request.headers.get("Idempotency-Key")
        if not idem_key:
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": {
                            "code": "MISSING_IDEMPOTENCY_KEY",
                            "message": "Idempotency-Key header is required for this endpoint",
                        },
                    }
                ),
                400,
            )

        scope = request.path  # e.g. '/v1/docs/clearance-pack'

        # --- Check for existing record ---
        existing: Optional[IdempotencyRecord] = (
            db.session.query(IdempotencyRecord)
            .filter_by(scope=scope, idempotency_key=idem_key)
            .first()
        )

        if existing is not None:
            if existing.status == "COMPLETED":
                logger.info(
                    f"Idempotency hit (COMPLETED): scope={scope} key={idem_key}"
                )
                return (
                    jsonify(existing.response_body or {}),
                    existing.response_code or 200,
                )
            elif existing.status == "IN_PROGRESS":
                logger.warning(
                    f"Idempotency conflict (IN_PROGRESS): scope={scope} key={idem_key}"
                )
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": {
                                "code": "CONFLICT",
                                "message": "A request with this Idempotency-Key is already being processed",
                            },
                        }
                    ),
                    409,
                )
            elif existing.status == "FAILED":
                # Allow retry: delete the old failed record
                logger.info(f"Idempotency retry (FAILED): scope={scope} key={idem_key}")
                db.session.delete(existing)
                db.session.flush()

        # --- Insert new IN_PROGRESS record ---
        record = IdempotencyRecord(
            scope=scope,
            idempotency_key=idem_key,
            status="IN_PROGRESS",
        )
        db.session.add(record)
        try:
            db.session.flush()
        except IntegrityError:
            # Race condition: another request beat us (parallel INSERT)
            db.session.rollback()
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": {
                            "code": "CONFLICT",
                            "message": "A request with this Idempotency-Key is already being processed",
                        },
                    }
                ),
                409,
            )

        # --- Execute the actual view ---
        try:
            response = f(*args, **kwargs)

            # Parse the response to store in the record
            if isinstance(response, tuple):
                resp_obj, status_code = response[0], response[1]
            else:
                resp_obj, status_code = response, 200

            # Extract JSON body from response
            try:
                if hasattr(resp_obj, "get_json"):
                    body = resp_obj.get_json(silent=True)
                elif hasattr(resp_obj, "json"):
                    body = resp_obj.json
                elif hasattr(resp_obj, "get_data"):
                    body = json.loads(resp_obj.get_data(as_text=True))
                else:
                    body = None  # Unable to extract JSON body
            except Exception:
                body = None

            # Update the record to COMPLETED
            record.status = "COMPLETED"
            record.response_code = status_code
            record.response_body = body
            db.session.commit()

            return response

        except Exception as exc:
            # Mark as FAILED so the key can be retried
            try:
                record.status = "FAILED"
                db.session.commit()
            except Exception:
                db.session.rollback()
            raise exc

    return decorated_function
