
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.simulator.provider_simulator import provider_simulator
from payment_lab.workers.status_worker import StatusWorker


@pytest.mark.asyncio
async def test_ts_026_provider_timeout_becomes_unknown(client: AsyncClient):
    # TS-026: Provider timeout -> UNKNOWN, no auto-retry charge
    resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "ref_timeout_026",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_timeout_026"},
    )
    payment_id = resp.json()["id"]

    # Confirm with timeout_success scenario
    conf_resp = await client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=timeout_success")
    assert conf_resp.status_code == 200
    data = conf_resp.json()
    assert data["status"] == "UNKNOWN"
    assert data["provider_reference"] is not None

    # Verify provider charge count is exactly 1 (INV-04)
    assert provider_simulator.get_charge_count(payment_id) == 1


@pytest.mark.asyncio
async def test_ts_027_timeout_then_status_worker_succeeds(client: AsyncClient, db_session: AsyncSession):
    # TS-027: Timeout, but provider actually succeeded -> Worker resolves to SUCCEEDED
    resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "ref_timeout_027",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_timeout_027"},
    )
    payment_id = resp.json()["id"]

    await client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=timeout_success")

    # Run StatusWorker query
    updated_payment = await StatusWorker.process_unknown_payment(db_session, payment_id, current_attempt=1)
    assert updated_payment.status == "SUCCEEDED"
    assert updated_payment.succeeded_at is not None


@pytest.mark.asyncio
async def test_ts_028_timeout_then_status_worker_fails(client: AsyncClient, db_session: AsyncSession):
    # TS-028: Timeout and provider actually declined -> Worker resolves to FAILED
    resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "ref_timeout_028",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_timeout_028"},
    )
    payment_id = resp.json()["id"]

    await client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=timeout_fail")

    updated_payment = await StatusWorker.process_unknown_payment(db_session, payment_id, current_attempt=1)
    assert updated_payment.status == "FAILED"


@pytest.mark.asyncio
async def test_ts_029_exhausted_queries_sets_needs_review(client: AsyncClient, db_session: AsyncSession):
    # TS-029: 5 queries exhausted still UNKNOWN -> needs_review=True, status remains UNKNOWN
    resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "ref_timeout_029",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_timeout_029"},
    )
    payment_id = resp.json()["id"]

    # Simulates provider whose status remains unknown
    await client.post(f"/api/v1/payments/{payment_id}/confirm?scenario=timeout_unknown")

    # Force status query attempt 5
    pay = await StatusWorker.process_unknown_payment(db_session, payment_id, current_attempt=5)
    assert pay.needs_review is True

