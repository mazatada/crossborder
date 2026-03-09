"""Tests for API-level idempotency middleware (Phase 4a)."""


class TestIdempotencyMiddleware:
    """Test the require_idempotency_key decorator."""

    # ── POST /v1/docs/clearance-pack ──

    def test_missing_idempotency_key_returns_400(self, client):
        """Idempotency-Key ヘッダーがない場合は 400 を返す。"""
        resp = client.post(
            "/v1/docs/clearance-pack",
            json={
                "hs_code": "0901.11",
                "required_uom": "KG",
                "invoice_uom": "KG",
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "MISSING_IDEMPOTENCY_KEY"

    def test_first_request_succeeds(self, client, db_session):
        """初回リクエストは正常に処理される。"""
        resp = client.post(
            "/v1/docs/clearance-pack",
            headers={"Idempotency-Key": "test-key-001"},
            json={
                "hs_code": "0901.11",
                "required_uom": "KG",
                "invoice_uom": "KG",
            },
        )
        assert resp.status_code == 202
        data = resp.get_json()
        assert "job_id" in data

        # IdempotencyRecord が COMPLETED で保存されていることを確認
        from app.models import IdempotencyRecord

        record = (
            db_session.query(IdempotencyRecord)
            .filter_by(
                scope="/v1/docs/clearance-pack",
                idempotency_key="test-key-001",
            )
            .first()
        )
        assert record is not None
        assert record.status == "COMPLETED"
        assert record.response_code == 202

    def test_duplicate_key_returns_cached_response(self, client, db_session):
        """同じ Idempotency-Key で2回目のリクエストはキャッシュされたレスポンスを返す。"""
        headers = {"Idempotency-Key": "test-key-dup"}
        payload = {
            "hs_code": "0901.11",
            "required_uom": "KG",
            "invoice_uom": "KG",
        }

        # 1st request
        resp1 = client.post("/v1/docs/clearance-pack", headers=headers, json=payload)
        assert resp1.status_code == 202
        data1 = resp1.get_json()

        # 2nd request with same key
        resp2 = client.post("/v1/docs/clearance-pack", headers=headers, json=payload)
        assert resp2.status_code == 202
        data2 = resp2.get_json()

        # Should return exactly the same job_id (cached)
        assert data2["job_id"] == data1["job_id"]

    def test_different_scope_allows_same_key(self, client, db_session):
        """異なるスコープ（異なるエンドポイント）で同じキーは別物として扱う。"""
        from app.models import IdempotencyRecord

        # Manually insert a record for a different scope
        existing = IdempotencyRecord(
            scope="/v1/other-endpoint",
            idempotency_key="shared-key-001",
            status="COMPLETED",
            response_code=200,
            response_body={"old": True},
        )
        db_session.add(existing)
        db_session.flush()

        # Request to docs endpoint with same key should succeed (different scope)
        resp = client.post(
            "/v1/docs/clearance-pack",
            headers={"Idempotency-Key": "shared-key-001"},
            json={
                "hs_code": "0901.11",
                "required_uom": "KG",
                "invoice_uom": "KG",
            },
        )
        assert resp.status_code == 202

    def test_failed_record_allows_retry(self, client, db_session):
        """FAILED レコードが残っている場合はリトライを許可する。"""
        from app.models import IdempotencyRecord

        # Insert a FAILED record
        failed = IdempotencyRecord(
            scope="/v1/docs/clearance-pack",
            idempotency_key="retry-key-001",
            status="FAILED",
        )
        db_session.add(failed)
        db_session.flush()

        # Should succeed (FAILED record is deleted and retried)
        resp = client.post(
            "/v1/docs/clearance-pack",
            headers={"Idempotency-Key": "retry-key-001"},
            json={
                "hs_code": "0901.11",
                "required_uom": "KG",
                "invoice_uom": "KG",
            },
        )
        assert resp.status_code == 202

    def test_in_progress_returns_409(self, client, db_session):
        """IN_PROGRESS のレコードがある場合は 409 Conflict を返す。"""
        from app.models import IdempotencyRecord

        # Insert an IN_PROGRESS record to simulate concurrent request
        in_progress = IdempotencyRecord(
            scope="/v1/docs/clearance-pack",
            idempotency_key="conflict-key-001",
            status="IN_PROGRESS",
        )
        db_session.add(in_progress)
        db_session.flush()

        resp = client.post(
            "/v1/docs/clearance-pack",
            headers={"Idempotency-Key": "conflict-key-001"},
            json={
                "hs_code": "0901.11",
                "required_uom": "KG",
                "invoice_uom": "KG",
            },
        )
        assert resp.status_code == 409
        data = resp.get_json()
        assert data["error"]["code"] == "CONFLICT"

    # ── POST /v1/shipments (requires api key) ──

    def test_shipments_missing_idempotency_key(self, client, api_key_header):
        """Shipment 作成 API でも Idempotency-Key がなければ 400。"""
        resp = client.post(
            "/v1/shipments",
            headers=api_key_header,
            json={
                "destination_country": "US",
                "shipping_mode": "air",
                "lines": [],
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "MISSING_IDEMPOTENCY_KEY"
