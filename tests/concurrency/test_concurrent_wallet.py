import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.core.config import settings
from payment_lab.domain.invariants import assert_inv_03_wallet_balance_non_negative
from payment_lab.db.models import PaymentMethod, Wallet
from payment_lab.services.wallet_service import WalletService


@pytest.mark.asyncio
async def test_ts_033_wallet_concurrent_payments_balance_invariant(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    TS-033: Wallet with 100,000 VND. Two concurrent payments of 70,000 VND each.
    Expected: One succeeds, one gets INSUFFICIENT_FUNDS. Balance remains >= 0 and equals 30,000 VND (INV-03).
    """
    # 1. Setup payment method of type WALLET
    pm_id = "pm_wallet_ts033"
    pm = PaymentMethod(
        id=pm_id,
        merchant_id="m_active_1",
        type="WALLET",
        token="wallet_tok_100k",
    )
    db_session.add(pm)
    await db_session.commit()

    # Setup initial wallet balance = 100,000 VND
    wallet = await WalletService.get_or_create_wallet(
        session=db_session,
        payment_method_id=pm_id,
        initial_balance=100_000,
        currency="VND",
    )
    assert wallet.balance == 100_000

    # 2. Create Payment 1 and Payment 2
    r1 = await client.post(
        "/api/v1/payments",
        json={
            "amount": 70_000,
            "currency": "VND",
            "merchant_reference": "ref_wallet_p1",
            "payment_method_id": pm_id,
        },
        headers={"Idempotency-Key": "idem_wallet_p1"},
    )
    p1_id = r1.json()["id"]

    r2 = await client.post(
        "/api/v1/payments",
        json={
            "amount": 70_000,
            "currency": "VND",
            "merchant_reference": "ref_wallet_p2",
            "payment_method_id": pm_id,
        },
        headers={"Idempotency-Key": "idem_wallet_p2"},
    )
    p2_id = r2.json()["id"]

    # 3. Confirm both simultaneously
    t1 = client.post(f"/api/v1/payments/{p1_id}/confirm?scenario=success")
    t2 = client.post(f"/api/v1/payments/{p2_id}/confirm?scenario=success")
    resp1, resp2 = await asyncio.gather(t1, t2)

    status_codes = {resp1.status_code, resp2.status_code}
    assert 200 in status_codes
    assert 422 in status_codes  # 422 INSUFFICIENT_FUNDS

    # Verify wallet balance is exactly 30,000 and non-negative (INV-03)
    await db_session.refresh(wallet)
    assert wallet.balance == 30_000
    assert_inv_03_wallet_balance_non_negative(wallet.balance)

