
import pytest
from httpx import AsyncClient


async def create_succeeded_payment(client: AsyncClient, amount: int = 1_000_000, key: str = "key_pay_ref") -> str:
    create_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": amount,
            "currency": "VND",
            "merchant_reference": f"order_{key}",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": f"idem_{key}"},
    )
    payment_id = create_resp.json()["id"]
    await client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=success")
    return payment_id


@pytest.mark.asyncio
async def test_ts_034_full_refund(client: AsyncClient):
    payment_id = await create_succeeded_payment(client, amount=100_000, key="ts034")

    resp = await client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 100_000, "currency": "VND", "reason": "Full refund"},
        headers={"Idempotency-Key": "idem_refund_ts034"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "SUCCEEDED"

    list_resp = await client.get(f"/api/v1/payments/{payment_id}/refunds")
    assert list_resp.json()["refundable_amount"] == 0


@pytest.mark.asyncio
async def test_ts_035_partial_refunds_30_and_70(client: AsyncClient):
    payment_id = await create_succeeded_payment(client, amount=100_000, key="ts035")

    # Refund 1: 30,000
    r1 = await client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 30_000, "currency": "VND"},
        headers={"Idempotency-Key": "idem_refund_ts035_1"},
    )
    assert r1.status_code == 201
    assert r1.json()["status"] == "SUCCEEDED"

    # Refund 2: 70,000
    r2 = await client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 70_000, "currency": "VND"},
        headers={"Idempotency-Key": "idem_refund_ts035_2"},
    )
    assert r2.status_code == 201
    assert r2.json()["status"] == "SUCCEEDED"

    list_resp = await client.get(f"/api/v1/payments/{payment_id}/refunds")
    assert list_resp.json()["refundable_amount"] == 0


@pytest.mark.asyncio
async def test_ts_036_refundable_boundary_exact_and_plus_one(client: AsyncClient):
    payment_id = await create_succeeded_payment(client, amount=50_000, key="ts036")

    # +1 exceeds refundable
    r_exceed = await client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 50_001, "currency": "VND"},
        headers={"Idempotency-Key": "idem_refund_ts036_fail"},
    )
    assert r_exceed.status_code == 422
    assert r_exceed.json()["error"]["code"] == "REFUND_EXCEEDS_REFUNDABLE"

    # Exact amount succeeds
    r_exact = await client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 50_000, "currency": "VND"},
        headers={"Idempotency-Key": "idem_refund_ts036_ok"},
    )
    assert r_exact.status_code == 201
    assert r_exact.json()["status"] == "SUCCEEDED"


@pytest.mark.asyncio
async def test_ts_037_refund_non_succeeded_payment(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "order_ts037",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_ts037"},
    )
    payment_id = create_resp.json()["id"]

    # Try to refund CREATED payment
    resp = await client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 10_000, "currency": "VND"},
        headers={"Idempotency-Key": "idem_refund_ts037"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "PAYMENT_NOT_REFUNDABLE"


@pytest.mark.asyncio
async def test_ts_038_currency_mismatch(client: AsyncClient):
    payment_id = await create_succeeded_payment(client, amount=100_000, key="ts038")

    resp = await client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 50, "currency": "USD"},
        headers={"Idempotency-Key": "idem_refund_ts038"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "REFUND_CURRENCY_MISMATCH"


@pytest.mark.asyncio
async def test_ts_043_maker_checker_large_refund(client: AsyncClient):
    payment_id = await create_succeeded_payment(client, amount=20_000_000, key="ts043")

    # Create refund >= 10,000,000 VND -> requires approval
    resp = await client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 10_000_000, "currency": "VND"},
        headers={"Idempotency-Key": "idem_refund_ts043", "X-User-ID": "user_maker"},
    )
    assert resp.status_code == 201
    refund_data = resp.json()
    assert refund_data["status"] == "PENDING_APPROVAL"
    refund_id = refund_data["id"]

    # Self-approval by maker must fail (403 SELF_APPROVAL_NOT_ALLOWED)
    approve_self = await client.post(
        f"/api/v1/refunds/{refund_id}/approve",
        json={"approved_by": "user_maker"},
    )
    assert approve_self.status_code == 403
    assert approve_self.json()["error"]["code"] == "SELF_APPROVAL_NOT_ALLOWED"

    # Approval by checker succeeds
    approve_checker = await client.post(
        f"/api/v1/refunds/{refund_id}/approve",
        json={"approved_by": "user_checker"},
    )
    assert approve_checker.status_code == 200
    assert approve_checker.json()["status"] == "SUCCEEDED"
    assert approve_checker.json()["approved_by"] == "user_checker"


@pytest.mark.asyncio
async def test_ts_044_max_10_refunds_limit(client: AsyncClient):
    payment_id = await create_succeeded_payment(client, amount=100_000, key="ts044")

    # Execute 10 refunds of 1,000 VND each
    for i in range(10):
        r = await client.post(
            f"/api/v1/payments/{payment_id}/refunds",
            json={"amount": 1_000, "currency": "VND"},
            headers={"Idempotency-Key": f"idem_refund_limit_{i}"},
        )
        assert r.status_code == 201

    # 11th refund must be rejected
    r11 = await client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 1_000, "currency": "VND"},
        headers={"Idempotency-Key": "idem_refund_limit_11"},
    )
    assert r11.status_code == 422
    assert r11.json()["error"]["code"] == "REFUND_LIMIT_REACHED"
