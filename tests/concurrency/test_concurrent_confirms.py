import asyncio
import pytest
from httpx import AsyncClient
from payment_lab.simulator.provider_simulator import provider_simulator


@pytest.mark.asyncio
async def test_ts_031_two_concurrent_confirms_single_provider_call(client: AsyncClient):
    """
    TS-031: Two concurrent confirm requests on the same payment.
    Expected: Exactly one call to upstream provider (INV-04); other request receives 409 or replayed result.
    """
    create_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "ref_concurrent_ts031",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_ts031_create"},
    )
    payment_id = create_resp.json()["id"]

    # Send 2 confirms simultaneously
    t1 = client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=success")
    t2 = client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=success")
    r1, r2 = await asyncio.gather(t1, t2)

    status_codes = {r1.status_code, r2.status_code}
    # One succeeds (200), other is rejected with 409 (INVALID_STATE_TRANSITION)
    assert 200 in status_codes
    assert 409 in status_codes

    # Verify provider charge count for this payment is strictly 1 (INV-04)
    assert provider_simulator.get_charge_count(payment_id) == 1

