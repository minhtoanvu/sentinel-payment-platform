"""Script to seed realistic demo data for SentinelQA - Payment Lab."""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.db.models import (
    Base,
    Merchant,
    Payment,
    PaymentMethod,
    PaymentStatusHistory,
    Refund,
    RefundStatusHistory,
    Wallet,
)
from payment_lab.db.session import async_session_factory, engine, init_db


async def seed_data():
    print("Initializing DB tables...")
    await init_db()

    async with async_session_factory() as session:
        now = datetime.now(timezone.utc)

        # 1. Merchants
        print("Seeding merchants...")
        m1 = Merchant(id="m_active_1", name="Alpha Coffee Roasters", status="ACTIVE", created_at=now - timedelta(days=30))
        m2 = Merchant(id="m_active_2", name="Beta Gadgets Store", status="ACTIVE", created_at=now - timedelta(days=20))
        m3 = Merchant(id="m_inactive_1", name="Legacy Store", status="INACTIVE", created_at=now - timedelta(days=60))
        session.add_all([m1, m2, m3])

        # 2. Payment Methods & Wallets
        print("Seeding payment methods & wallets...")
        pm1 = PaymentMethod(id="pm_card_1", merchant_id="m_active_1", type="CARD_TOKEN", token="tok_visa_4242", created_at=now)
        pm2 = PaymentMethod(id="pm_wallet_1", merchant_id="m_active_1", type="WALLET", token="wallet_usr_01", created_at=now)
        session.add_all([pm1, pm2])

        w1 = Wallet(payment_method_id="pm_wallet_1", balance=5_000_000, currency="VND", updated_at=now)
        session.add(w1)

        # 3. Payments in Various Lifecycle States
        print("Seeding payments across lifecycle states...")

        # Payment A: SUCCEEDED
        p_succ = Payment(
            id=str(uuid.uuid4()),
            public_id="pay_demo_succeeded_01",
            merchant_id="m_active_1",
            merchant_reference="order_succ_101",
            payment_method_id="pm_card_1",
            amount=500_000,
            currency="VND",
            status="SUCCEEDED",
            refunded_amount=0,
            needs_review=False,
            provider_reference="sim_ch_demo_succ_01",
            succeeded_at=now - timedelta(hours=2),
            created_at=now - timedelta(hours=2, minutes=5),
            updated_at=now - timedelta(hours=2),
        )
        session.add(p_succ)
        session.add(
            PaymentStatusHistory(
                id=str(uuid.uuid4()),
                payment_id=p_succ.id,
                from_status="CREATED",
                to_status="SUCCEEDED",
                reason="Provider charge approved",
                actor="PROVIDER",
                at=now - timedelta(hours=2),
            )
        )

        # Payment B: CREATED (Pending confirm)
        p_created = Payment(
            id=str(uuid.uuid4()),
            public_id="pay_demo_created_02",
            merchant_id="m_active_1",
            merchant_reference="order_created_102",
            payment_method_id="pm_card_1",
            amount=150_000,
            currency="VND",
            status="CREATED",
            refunded_amount=0,
            needs_review=False,
            expires_at=now + timedelta(minutes=25),
            created_at=now - timedelta(minutes=5),
            updated_at=now - timedelta(minutes=5),
        )
        session.add(p_created)

        # Payment C: UNKNOWN (Timed out, needs review)
        p_unknown = Payment(
            id=str(uuid.uuid4()),
            public_id="pay_demo_unknown_03",
            merchant_id="m_active_1",
            merchant_reference="order_unknown_103",
            payment_method_id="pm_card_1",
            amount=1_200_000,
            currency="VND",
            status="UNKNOWN",
            refunded_amount=0,
            needs_review=True,
            provider_reference="sim_ch_demo_unk_03",
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(minutes=10),
        )
        session.add(p_unknown)

        # Payment D: SUCCEEDED with partial refund
        p_part_ref = Payment(
            id=str(uuid.uuid4()),
            public_id="pay_demo_refunded_04",
            merchant_id="m_active_1",
            merchant_reference="order_ref_104",
            payment_method_id="pm_card_1",
            amount=2_000_000,
            currency="VND",
            status="SUCCEEDED",
            refunded_amount=600_000,
            needs_review=False,
            provider_reference="sim_ch_demo_ref_04",
            succeeded_at=now - timedelta(days=1),
            created_at=now - timedelta(days=1, minutes=10),
            updated_at=now - timedelta(hours=12),
        )
        session.add(p_part_ref)

        ref1 = Refund(
            id=str(uuid.uuid4()),
            public_id="ref_demo_01",
            payment_id=p_part_ref.id,
            amount=600_000,
            currency="VND",
            status="SUCCEEDED",
            reason="Customer partial return",
            created_by="support_agent",
            approved_by="support_lead",
            provider_reference="sim_ref_demo_01",
            created_at=now - timedelta(hours=12),
            updated_at=now - timedelta(hours=12),
        )
        session.add(ref1)

        await session.commit()
        print("Demo data seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
