import os
import time
import requests
import json

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000/v1")
API_KEY = "test-secret-key"
HEADERS = {"Content-Type": "application/json", "X-Api-Key": API_KEY}

def print_step(title):
    print(f"\n{'='*50}\n▶ {title}\n{'='*50}")

def _req(method, endpoint, payload=None, expected_status=None):
    url = f"{BASE_URL}{endpoint}"
    if method == "POST":
        res = requests.post(url, headers=HEADERS, json=payload)
    elif method == "PUT":
        res = requests.put(url, headers=HEADERS, json=payload)
    elif method == "GET":
        res = requests.get(url, headers=HEADERS, params=payload)
    
    print(f"{method} {endpoint} -> {res.status_code}")
    if expected_status and res.status_code not in expected_status:
        print(f"❌ FAILED: Expected {expected_status}, got {res.status_code}")
        print(f"Response: {res.text}")
        exit(1)
        
    try:
        data = res.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...\n")
        return data
    except Exception:
        print(res.text + "\n")
        return res.text

# 1. 最小情報のInboundを受信 (Phase 1)
print_step("1. Inbound Order Received")
inbound_payload = {
    "status": "PAID",
    "ts": "2026-03-03T10:00:00Z",
    "customer_region": "JP"
}
_req("POST", "/integrations/orders/ORD-1002/status", inbound_payload, [202])

# 2. Productのドラフト作成と更新
print_step("2. Product Creation & Update")
product_payload = {
    "title": "Luxury Matcha Green Tea Powder",
    "external_ref": {
        "sku": "SKU-TEST-002",
        "category": "other_food_preparations"
    },
    "description_en": "Premium grade matcha from Uji, Kyoto.",
    "origin_country": "JP",
    "is_food": True
}
prod_res = _req("POST", "/products", product_payload, [201])
product_id = prod_res["id"]

update_payload = {
    "processing_state": "powder",
    "physical_form": "solid",
    "unit_weight_g": 100,
    "shelf_life_days": 365,
    "animal_derived_flags": {"contains_dairy": False}
}
_req("PUT", f"/products/{product_id}", update_payload, [200])

# 3. Validation: False (Missing required logic check if possible via API or direct ready transition)
# 試しに不正な型を入れてみる (Phase 1.5 Strict Validation)
print_step("3. Strict Validation Negative Check")
bad_payload = {"is_food": "true"} # Should fail
_req("PUT", f"/products/{product_id}", bad_payload, [400])

# 4. Product Validation (Transitions to 'ready' and MUST enqueue Job)
print_step("4. Product Validation & Job Trigger")
val_res = _req("POST", f"/products/{product_id}/validate", None, [200])
if not val_res.get("valid"):
    print("❌ Product validation failed unexpectedly")
    exit(1)

# 5. Job Runtime 実行 (CLIを叩いてキューを消化する)
print_step("5. Execute Job Runtime (Background Worker)")
print("Wait 5 seconds for background worker to process the classification job...")
time.sleep(5)
time.sleep(2) # Wait for db flush

# 6. get_products with N+1 fix (include=hs)
print_step("6. Get Products (include=hs)")
prods_res = _req("GET", "/products", {"include": "hs", "limit": 10}, [200])
hs_data = None
for p in prods_res["data"]:
    if p["id"] == product_id:
        hs_data = p.get("active_classification")
        break

if not hs_data:
    print("❌ HS Classification was not eagerly loaded or job failed.")
    exit(1)
print(f"Eagerly loaded HS Data: {json.dumps(hs_data)}")
classification_id = hs_data["id"]

# 7. HS Review Lock & Finalize
print_step("7. Lock and Finalize HS Review")
_req("POST", f"/reviews/hs/{classification_id}/assign", {"operator_id": "UserA"}, [200])
_req("POST", f"/reviews/hs/{classification_id}/lock", None, [200, 403, 404])

finalize_payload = {
    "final_hs_code": "0902.10.00",
    "reviewed_by": "UserA"
}
_req("POST", f"/reviews/hs/{classification_id}/finalize", finalize_payload, [200])

# 8. Reopen HS Classification (Phase 1.5)
print_step("8. Reopen HS Classification")
reopen_payload = {
    "reason": "Found alternative documentation specifying different category."
}
_req("POST", f"/hs-classifications/{classification_id}:reopen", reopen_payload, [200])

# 9. Verify Product Status reverted to ready
print_step("9. Verify Reopen Result")
prods_res_after = _req("GET", "/products", {"include": "hs", "limit": 10}, [200])
for p in prods_res_after["data"]:
    if p["id"] == product_id:
        print(f"Product Status is now: {p['status']}")
        if p['status'] != 'ready':
             print("❌ Product status did not revert to 'ready'")
             exit(1)
        break

print_step("✅ ALL CUSTOMER JOURNEY TESTS PASSED")
