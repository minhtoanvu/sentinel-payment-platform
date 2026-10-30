import json
import time
import pytest
from httpx import AsyncClient
from payment_lab.simulator.provider_simulator import provider_simulator


@pytest.mark.asyncio
async def test_ts_045_valid_webhook_payment_succeeded(client: AsyncClient):
    # Create payment in PROCESSING / CREATED
    p_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 250_000,
            "currency": "VND",
            "merchant_reference": "order_wh_045",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_wh_045"},
    )
    payment_id = p_resp.json()["id"]

    now_ts = int(time.time())
    payload = {
        "event_id": "evt_ts045_valid",
        "event_type": "payment.succeeded",
        "data": {"payment_id": payment_id, "amount": 250_000},
    }
    payload_str = json.dumps(payload)
    sig = provider_simulator.sign_payload(now_ts, payload_str)

    headers = {
        "X-Provider-Timestamp": str(now_ts),
        "X-Provider-Signature": sig,
        "Content-Type": "application/json",
    }
    resp = await client.post("/api/v1/webhooks/provider", content=payload_str, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"
    assert resp.json()["processing_status"] == "PROCESSED"

    # Check payment status updated to SUCCEEDED
    get_resp = await client.get(f"/api/v1/payments/{payment_id}")
    assert get_resp.json()["status"] == "SUCCEEDED"


@pytest.mark.asyncio
async def test_ts_046_bad_or_missing_signature(client: AsyncClient):
    payload = {"event_id": "evt_bad_sig", "event_type": "payment.succeeded"}
    payload_str = json.dumps(payload)
    now_ts = int(time.time())

    # Missing signature header
    resp_missing = await client.post(
        "/api/v1/webhooks/provider",
        content=payload_str,
        headers={"X-Provider-Timestamp": str(now_ts), "Content-Type": "application/json"},
    )
    assert resp_missing.status_code == 401
    assert resp_missing.json()["error"]["code"] == "INVALID_SIGNATURE"

    # Wrong signature
    resp_wrong = await client.post(
        "/api/v1/webhooks/provider",
        content=payload_str,
        headers={
            "X-Provider-Timestamp": str(now_ts),
            "X-Provider-Signature": "invalid_hex_signature",
            "Content-Type": "application/json",
        },
    )
    assert resp_wrong.status_code == 401
    assert resp_wrong.json()["error"]["code"] == "INVALID_SIGNATURE"


@pytest.mark.asyncio
async def test_ts_047_timestamp_out_of_range(client: AsyncClient):
    payload = {"event_id": "evt_stale_ts", "event_type": "payment.succeeded"}
    payload_str = json.dumps(payload)
    # 10 minutes ago (> 300s)
    old_ts = int(time.time()) - 600
    sig = provider_simulator.sign_payload(old_ts, payload_str)

    resp = await client.post(
        "/api/v1/webhooks/provider",
        content=payload_str,
        headers={
            "X-Provider-Timestamp": str(old_ts),
            "X-Provider-Signature": sig,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] in ("WEBHOOK_TIMESTAMP_OUT_OF_RANGE", "INVALID_SIGNATURE")


@pytest.mark.asyncio
async def test_ts_048_webhook_deduplication(client: AsyncClient):
    now_ts = int(time.time())
    payload = {
        "event_id": "evt_dedup_048",
        "event_type": "payment.succeeded",
        "data": {"payment_id": "non_existent"},
    }
    payload_str = json.dumps(payload)
    sig = provider_simulator.sign_payload(now_ts, payload_str)
    headers = {
        "X-Provider-Timestamp": str(now_ts),
        "X-Provider-Signature": sig,
        "Content-Type": "application/json",
    }

    # First delivery
    resp1 = await client.post("/api/v1/webhooks/provider", content=payload_str, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["deduplicated"] is False

    # Second delivery (replay)
    resp2 = await client.post("/api/v1/webhooks/provider", content=payload_str, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["deduplicated"] is True


@pytest.mark.asyncio
async def test_ts_050_webhook_orphan_payment(client: AsyncClient):
    now_ts = int(time.time())
    payload = {
        "event_id": "evt_orphan_050",
        "event_type": "payment.succeeded",
        "data": {"payment_id": "non_existent_payment_id"},
    }
    payload_str = json.dumps(payload)
    sig = provider_simulator.sign_payload(now_ts, payload_str)
    headers = {
        "X-Provider-Timestamp": str(now_ts),
        "X-Provider-Signature": sig,
        "Content-Type": "application/json",
    }

    resp = await client.post("/api/v1/webhooks/provider", content=payload_str, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["processing_status"] == "ORPHAN"


@pytest.mark.asyncio
async def test_ts_052_unknown_event_type_ignored(client: AsyncClient):
    now_ts = int(time.time())
    payload = {
        "event_id": "evt_unknown_type",
        "event_type": "custom.unknown.event",
    }
    payload_str = json.dumps(payload)
    sig = provider_simulator.sign_payload(now_ts, payload_str)
    headers = {
        "X-Provider-Timestamp": str(now_ts),
        "X-Provider-Signature": sig,
        "Content-Type": "application/json",
    }

    resp = await client.post("/api/v1/webhooks/provider", content=payload_str, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["processing_status"] == "IGNORED"

