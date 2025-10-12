from functools import wraps
from flask import request, jsonify

def require_json(f):
    @wraps(f)
    def inner(*a, **k):
        if not request.is_json: return jsonify({"error":{"class":"missing_required","message":"JSON required"}}), 400
        return f(*a, **k)
    return inner

def ensure_required(fields: dict):
    return [k for k,v in fields.items() if not v]
