from typing import Any, Callable, Dict, List, Optional


def contains_any_ids(field_value: Any, values: List[str]) -> bool:
    if not field_value:
        return False
    ingredient_ids = [ing.get("id") for ing in field_value if isinstance(ing, dict)]
    return any(ing_id in values for ing_id in ingredient_ids)


def process_any(field_value: Any, values: List[str]) -> bool:
    if not field_value or not isinstance(field_value, list):
        return False
    processes = [p.lower() for p in field_value]
    return any(v.lower() in processes for v in values)


def origin_in(field_value: Any, values: List[str]) -> bool:
    if not field_value:
        return False
    return field_value.upper() in [v.upper() for v in values]


def category_is(field_value: Any, value: str) -> bool:
    if not field_value:
        return False
    return field_value.lower() == value.lower()


def not_contains_ids(field_value: Any, values: List[str]) -> bool:
    return not contains_any_ids(field_value, values)


def ingredient_pct_threshold(
    field_value: Any,
    ingredient_id: str,
    min_pct: float,
    max_pct: Optional[float] = None,
) -> bool:
    if not field_value:
        return False
    for ing in field_value:
        if isinstance(ing, dict) and ing.get("id") == ingredient_id:
            pct = ing.get("pct", 0)
            if max_pct is None:
                return pct >= min_pct
            return min_pct <= pct <= max_pct
    return False


def always() -> bool:
    return True


PREDICATES: Dict[str, Callable[..., bool]] = {
    "contains_any_ids": contains_any_ids,
    "process_any": process_any,
    "origin_in": origin_in,
    "category_is": category_is,
    "not_contains_ids": not_contains_ids,
    "ingredient_pct_threshold": ingredient_pct_threshold,
    "always": always,
}


def validate_predicate_params(predicate: str, params: Dict[str, Any]) -> None:
    if predicate == "always":
        if params:
            raise ValueError("always does not accept params")
        return

    if predicate in ("contains_any_ids", "process_any", "origin_in", "not_contains_ids"):
        values = params.get("values")
        if not isinstance(values, list):
            raise ValueError(f"{predicate}.values must be a list")
        return

    if predicate == "category_is":
        value = params.get("value")
        if not isinstance(value, str):
            raise ValueError("category_is.value must be a string")
        return

    if predicate == "ingredient_pct_threshold":
        if "ingredient_id" not in params or "min_pct" not in params:
            raise ValueError("ingredient_pct_threshold requires ingredient_id and min_pct")
        if not isinstance(params.get("ingredient_id"), str):
            raise ValueError("ingredient_pct_threshold.ingredient_id must be a string")
        if not isinstance(params.get("min_pct"), (int, float)):
            raise ValueError("ingredient_pct_threshold.min_pct must be a number")
        max_pct = params.get("max_pct")
        if max_pct is not None and not isinstance(max_pct, (int, float)):
            raise ValueError("ingredient_pct_threshold.max_pct must be a number")
        return
