import json
import pytest
from httpx import AsyncClient
from payment_lab.core.config import settings
from payment_lab.core.errors import AmountAboveMaxError, RefundExceedsRefundableError
from payment_lab.domain.models import Currency
from payment_lab.domain.rules import validate_amount


@pytest.mark.asyncio
async def test_bug_001_refund_less_than_defect(client: AsyncClient):
    # Setup payment
    resp = await client.post(
        "/api/v1/payments",
        json={"amount": 100_000, "currency": "VND", "merchant_reference": "ref_bug001", "payment_method_id": "pm_card_1"},
        headers={"Idempotency-Key": "idem_bug001_p"},
    )
    p_id = resp.json()["id"]
    await client.post(f"/api/v1/payments/{p_id}/confirm?scenario=success")

    # With BUG-001 enabled: exact amount 100,000 is rejected!
    settings.PL_DEFECT_BUG_001 = True
    try:
        r_exact = await client.post(
            f"/api/v1/payments/{p_id}/refunds",
            json={"amount": 100_000, "currency": "VND"},
            headers={"Idempotency-Key": "idem_bug001_r"},
        )
        assert r_exact.status_code == 422
        assert r_exact.json()["error"]["code"] == "REFUND_EXCEEDS_REFUNDABLE"
    finally:
        settings.PL_DEFECT_BUG_001 = False


@pytest.mark.asyncio
async def test_bug_002_idempotency_payload_hash_ignored(client: AsyncClient):
    payload1 = {"amount": 100_000, "currency": "VND", "merchant_reference": "ref_bug002", "payment_method_id": "pm_card_1"}
    payload2 = {"amount": 900_000, "currency": "VND", "merchant_reference": "ref_bug002", "payment_method_id": "pm_card_1"}
    headers = {"Idempotency-Key": "idem_bug002", "X-Merchant-ID": "m_active_1"}

    # First call
    r1 = await client.post("/api/v1/payments", json=payload1, headers=headers)
    assert r1.status_code == 201

    # With BUG-002 enabled: different payload with same key does NOT fail with 422, returns old payment!
    settings.PL_DEFECT_BUG_002 = True
    try:
        r2 = await client.post("/api/v1/payments", json=payload2, headers=headers)
        assert r2.status_code in (200, 201)
        assert r2.json()["amount"] == 100_000  # Returns original payment instead of 422
    finally:
        settings.PL_DEFECT_BUG_002 = False


def test_bug_007_max_amount_boundary_defect():
    # Normal: 50,000,001 is rejected
    with pytest.raises(AmountAboveMaxError):
        validate_amount(50_000_001, Currency.VND)

    # With BUG-007 enabled: 50,000,001 is allowed!
    settings.PL_DEFECT_BUG_007 = True
    try:
        res = validate_amount(50_000_001, Currency.VND)
        assert res == 50_000_001
    finally:
        settings.PL_DEFECT_BUG_007 = False


@pytest.mark.asyncio
async def test_bug_006_webhook_without_signature_accepted(client: AsyncClient):
    payload = {"event_id": "evt_bug006", "event_type": "payment.succeeded"}
    payload_str = json.dumps(payload)

    # With BUG-006 enabled: webhook without signature is accepted with 200
    settings.PL_DEFECT_BUG_006 = True
    try:
        resp = await client.post(
            "/api/v1/webhooks/provider",
            content=payload_str,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "acknowledged"
    finally:
        settings.PL_DEFECT_BUG_006 = False


@pytest.mark.asyncio
async def test_bug_017_merchant_bola_defect(client: AsyncClient):
    # Merchant 1 creates payment
    resp = await client.post(
        "/api/v1/payments",
        json={"amount": 100_000, "currency": "VND", "merchant_reference": "ref_bug017", "payment_method_id": "pm_card_1"},
        headers={"Idempotency-Key": "idem_bug017", "X-Merchant-ID": "m_active_1"},
    )
    p_id = resp.json()["id"]

    # With BUG-017 enabled: Merchant 2 can read Merchant 1's payment!
    settings.PL_DEFECT_BUG_017 = True
    try:
        read_resp = await client.get(
            f"/api/v1/payments/{p_id}",
            headers={"X-Merchant-ID": "m_active_2"},
        )
        assert read_resp.status_code == 200
        assert read_resp.json()["id"] == p_id
    finally:
        settings.PL_DEFECT_BUG_017 = False

