import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from payment_lab.db.models import Payment
from tests.conftest import async_test_session_factory


@pytest.mark.asyncio
async def test_ts_015_twenty_concurrent_requests_same_idempotency_key(client: AsyncClient):
    """
    TS-015: 20 parallel requests with the same Idempotency-Key.
    Expected: Exactly one payment created in DB; remaining receive replay (200/201) or 409 REQUEST_IN_PROGRESS.
    """
    payload = {
        "amount": 250_000,
        "currency": "VND",
        "merchant_reference": "ref_concurrent_ts015",
        "payment_method_id": "pm_card_1",
    }
    headers = {
        "Idempotency-Key": "idem_key_ts015_parallel_20",
        "X-Merchant-ID": "m_active_1",
    }

    # Send 20 concurrent requests
    tasks = [client.post("/api/v1/payments", json=payload, headers=headers) for _ in range(20)]
    responses = await asyncio.gather(*tasks, return_exceptions=False)

    for r in responses:
        assert r.status_code in (200, 201, 409), f"Unexpected status {r.status_code}: {r.text}"

    created_payments = [r.json()["id"] for r in responses if r.status_code in (200, 201)]
    in_progress_responses = [r for r in responses if r.status_code == 409]

    assert len(created_payments) >= 1
    # All successful responses must return the EXACT same payment id
    assert len(set(created_payments)) == 1

    # Verify database has exactly 1 payment record
    async with async_test_session_factory() as session:
        stmt = select(Payment).where(Payment.merchant_reference == "ref_concurrent_ts015")
        payments = (await session.execute(stmt)).scalars().all()
        assert len(payments) == 1, f"Expected 1 record in DB, found {len(payments)}"
