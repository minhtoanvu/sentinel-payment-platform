import asyncio
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ts_040_concurrent_refunds_exceeding_total(client: AsyncClient):
    """
    TS-040: Payment of 100,000 VND. Two concurrent refunds of 60,000 VND.
    Expected: One succeeds, other rejected with REFUND_EXCEEDS_REFUNDABLE.
    Total refunded amount <= payment.amount (INV-02).
    """
    create_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "ref_concurrent_ts040",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_ts040_p"},
    )
    payment_id = create_resp.json()["id"]
    await client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=success")

    # Send two 60,000 VND refunds in parallel
    t1 = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 60_000, "currency": "VND"},
        headers={"Idempotency-Key": "idem_ts040_r1"},
    )
    t2 = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 60_000, "currency": "VND"},
        headers={"Idempotency-Key": "idem_ts040_r2"},
    )
    r1, r2 = await asyncio.gather(t1, t2)

    status_codes = {r1.status_code, r2.status_code}
    assert 201 in status_codes
    assert 422 in status_codes

    # Check remaining refundable and total refunded
    refund_list = (await client.get(f"/api/v1/payments/{payment_id}/refunds")).json()
    assert refund_list["refundable_amount"] == 40_000
    assert len(refund_list["refunds"]) == 1

