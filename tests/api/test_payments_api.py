import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ts_001_create_valid_payment_vnd(client: AsyncClient):
    payload = {
        "amount": 100_000,
        "currency": "VND",
        "merchant_reference": "order_123",
        "payment_method_id": "pm_card_1",
        "description": "Test order",
    }
    headers = {
        "Idempotency-Key": "idem_key_ts001_valid",
        "X-Merchant-ID": "m_active_1",
    }
    resp = await client.post("/api/v1/payments", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "CREATED"
    assert data["amount"] == 100_000
    assert data["currency"] == "VND"
    assert data["public_id"].startswith("pay_")
    assert data["expires_at"] is not None


@pytest.mark.asyncio
async def test_ts_002_missing_amount_field(client: AsyncClient):
    payload = {
        "currency": "VND",
        "merchant_reference": "order_missing_amt",
        "payment_method_id": "pm_card_1",
    }
    headers = {"Idempotency-Key": "idem_key_ts002"}
    resp = await client.post("/api/v1/payments", json=payload, headers=headers)
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_ts_012_idempotency_replay(client: AsyncClient):
    payload = {
        "amount": 200_000,
        "currency": "VND",
        "merchant_reference": "order_ts012",
        "payment_method_id": "pm_card_1",
    }
    headers = {
        "Idempotency-Key": "idem_key_ts012_exact",
        "X-Merchant-ID": "m_active_1",
    }
    # First call
    resp1 = await client.post("/api/v1/payments", json=payload, headers=headers)
    assert resp1.status_code == 201
    pay_id1 = resp1.json()["id"]

    # Replay call with exact same key and payload
    resp2 = await client.post("/api/v1/payments", json=payload, headers=headers)
    assert resp2.status_code in (200, 201)
    assert resp2.headers.get("Idempotent-Replayed") == "true"
    assert resp2.json()["id"] == pay_id1


@pytest.mark.asyncio
async def test_ts_013_idempotency_key_reused_diff_payload(client: AsyncClient):
    payload1 = {
        "amount": 100_000,
        "currency": "VND",
        "merchant_reference": "order_ts013",
        "payment_method_id": "pm_card_1",
    }
    payload2 = {
        "amount": 300_000,  # Changed amount!
        "currency": "VND",
        "merchant_reference": "order_ts013",
        "payment_method_id": "pm_card_1",
    }
    headers = {
        "Idempotency-Key": "idem_key_ts013_shared",
        "X-Merchant-ID": "m_active_1",
    }
    resp1 = await client.post("/api/v1/payments", json=payload1, headers=headers)
    assert resp1.status_code == 201

    # Second call with same key but different payload
    resp2 = await client.post("/api/v1/payments", json=payload2, headers=headers)
    assert resp2.status_code == 422
    assert resp2.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


@pytest.mark.asyncio
async def test_ts_014_idempotency_key_required_and_length(client: AsyncClient):
    payload = {
        "amount": 100_000,
        "currency": "VND",
        "merchant_reference": "order_ts014",
        "payment_method_id": "pm_card_1",
    }
    # Missing key
    resp_missing = await client.post("/api/v1/payments", json=payload)
    assert resp_missing.status_code == 400
    assert resp_missing.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    # Too short (< 8 chars)
    resp_short = await client.post(
        "/api/v1/payments", json=payload, headers={"Idempotency-Key": "short"}
    )
    assert resp_short.status_code == 400
    assert resp_short.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


@pytest.mark.asyncio
async def test_ts_018_confirm_success(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 500_000,
            "currency": "VND",
            "merchant_reference": "order_ts018",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_key_ts018"},
    )
    payment_id = create_resp.json()["id"]

    # Confirm with success scenario
    confirm_resp = await client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=success")
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()
    assert data["status"] == "SUCCEEDED"
    assert data["succeeded_at"] is not None
    assert data["provider_reference"] is not None


@pytest.mark.asyncio
async def test_ts_019_confirm_decline(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 500_000,
            "currency": "VND",
            "merchant_reference": "order_ts019",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_key_ts019"},
    )
    payment_id = create_resp.json()["id"]

    # Confirm with decline scenario
    confirm_resp = await client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=decline")
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()
    assert data["status"] == "FAILED"


@pytest.mark.asyncio
async def test_ts_020_confirm_already_succeeded(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 200_000,
            "currency": "VND",
            "merchant_reference": "order_ts020",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_key_ts020"},
    )
    payment_id = create_resp.json()["id"]
    await client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=success")

    # Confirm again
    confirm_again = await client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=success")
    assert confirm_again.status_code == 409
    assert confirm_again.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_ts_021_cancel_then_confirm(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 150_000,
            "currency": "VND",
            "merchant_reference": "order_ts021",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_key_ts021"},
    )
    payment_id = create_resp.json()["id"]

    # Cancel payment
    cancel_resp = await client.post(f"/api/v1/payments/{payment_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELED"

    # Confirm cancelled payment
    confirm_resp = await client.post(f"/api/v1/payments/{payment_id}/confirm")
    assert confirm_resp.status_code == 409
    assert confirm_resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_ts_032_duplicate_merchant_reference_prevented(client: AsyncClient):
    # Payment 1 with ref "order_dup_ref"
    resp1 = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "order_dup_ref",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_key_dup1"},
    )
    pay1_id = resp1.json()["id"]
    await client.post(f"/api/v1/payments/{pay1_id}/confirm?scenario=success")

    # Payment 2 with same ref "order_dup_ref"
    resp2 = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "order_dup_ref",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_key_dup2"},
    )
    pay2_id = resp2.json()["id"]

    # Confirming payment 2 should fail with ORDER_ALREADY_PAID (409)
    confirm2 = await client.post(f"/api/v1/payments/{pay2_id}/confirm?scenario=success")
    assert confirm2.status_code == 409
    assert confirm2.json()["error"]["code"] == "ORDER_ALREADY_PAID"


@pytest.mark.asyncio
async def test_ts_069_merchant_isolation_bola(client: AsyncClient):
    # Merchant 1 creates payment
    resp1 = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "order_bola_test",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_key_bola_1", "X-Merchant-ID": "m_active_1"},
    )
    pay_id = resp1.json()["id"]

    # Merchant 2 tries to read payment belonging to Merchant 1
    resp_bola = await client.get(
        f"/api/v1/payments/{pay_id}",
        headers={"X-Merchant-ID": "m_active_2"},
    )
    assert resp_bola.status_code in (403, 404)

