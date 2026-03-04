import time
import logging
from app.db import db
from app.models import Product, HSClassification
from app.classify import HSClassifier, ClassificationError
from app.audit import log_event
from app.jobs.handlers import register

logger = logging.getLogger(__name__)

@register("hs_classify")
def process(payload: dict, job_id: int = None, trace_id: str = None) -> dict:
    from app.jobs.cli import NonRetriableError
    
    product_id = payload.get("product_id")
    if not product_id:
        raise NonRetriableError("Missing product_id in payload")

    record = db.session.get(Product, product_id)
    if not record:
        raise NonRetriableError(f"Product {product_id} not found")
        
    if record.status != "ready":
        # Double queue check or changed status
        return {"skipped": True, "reason": f"Product status is {record.status}, expected 'ready'"}
        
    product_data = {
        "name": record.title,
        "category": record.external_ref.get("category") if record.external_ref else None,
        "origin_country": record.origin_country,
        "ingredients": record.external_ref.get("ingredients") if record.external_ref else None,
        "process": record.external_ref.get("process") if record.external_ref else None,
    }
    
    start_time = time.time()
    log_event(
        trace_id=trace_id,
        event="hs_classification_requested_async",
        product_name=record.title,
    )
    
    classifier = HSClassifier()
    try:
        result = classifier.classify(product_data)
    except ClassificationError as e:
        log_event(trace_id=trace_id, event="hs_classification_failed", error=str(e), product_name=record.title)
        raise ValueError(f"Classification failed: {e}")
        
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    hs_classification = HSClassification(
        product_id=record.id,
        trace_id=trace_id,
        product_name=record.title,
        category=product_data["category"],
        origin_country=product_data["origin_country"],
        ingredients=product_data["ingredients"],
        process=product_data["process"],
        hs_candidates=result["hs_candidates"],
        final_hs_code=result["final_hs_code"],
        required_uom=result["required_uom"],
        review_required=result["review_required"],
        duty_rate={"ad_valorem_rate": None, "ad_valorem_pct": None, "additional": []},
        risk_flags={"ad_cvd": False, "import_alert": False},
        status="classified",
        final_source="system",
        classification_method="rule_based",
        processing_time_ms=processing_time_ms,
        cache_hit=result.get("cache_hit", False),
        rules_version=classifier.get_rules_version(),
    )
    db.session.add(hs_classification)
    db.session.flush() # Flush to get HSClassification id
    
    # Update Product with new state and relation
    record.hs_base6 = result["final_hs_code"][:6] if result["final_hs_code"] else None
    record.active_classification_id = hs_classification.id
    record.status = "classification_review" if result["review_required"] else "validated"
    db.session.add(record)
    
    log_event(
        trace_id=trace_id,
        event="hs_classification_completed_async",
        final_hs_code=result["final_hs_code"],
        review_required=result["review_required"],
        product_id=record.id
    )
    
    return {
        "hs_classification_id": hs_classification.id,
        "final_hs_code": result["final_hs_code"],
        "review_required": result["review_required"]
    }
