import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.core.config import settings
from payment_lab.domain.models import PaymentStatus
from payment_lab.domain.state_machine import transition_payment
from payment_lab.db.models import Payment, PaymentAttempt, PaymentStatusHistory
from payment_lab.simulator.provider_simulator import provider_simulator


class StatusWorker:
    BACKOFF_SECONDS = [5, 10, 20, 40, 80]

    @staticmethod
    async def process_unknown_payment(
        session: AsyncSession,
        payment_id: str,
        current_attempt: int = 1,
    ) -> Payment:
        """
        Poll status for a payment in UNKNOWN status.
        Up to 5 attempts. If still UNKNOWN after 5 attempts, set needs_review = True.
        """
        now = datetime.now(timezone.utc)
        stmt = select(Payment).where(Payment.id == payment_id).with_for_update()
        res = await session.execute(stmt)
        payment = res.scalar_one_or_none()
        if not payment or payment.status != PaymentStatus.UNKNOWN.value:
            return payment

        provider_ref = payment.provider_reference or "unknown_ref"
        status_result = await provider_simulator.query_status(provider_ref)

        attempt = PaymentAttempt(
            id=str(uuid.uuid4()),
            payment_id=payment.id,
            attempt_no=current_attempt,
            outcome=status_result.status,
            provider_reference=provider_ref,
            created_at=now,
        )
        session.add(attempt)

        if status_result.status == "SUCCEEDED":
            new_status, _ = transition_payment(PaymentStatus.UNKNOWN, "status_success")
            payment.status = new_status.value
            payment.succeeded_at = now
            session.add(
                PaymentStatusHistory(
                    id=str(uuid.uuid4()),
                    payment_id=payment.id,
                    from_status=PaymentStatus.UNKNOWN.value,
                    to_status=new_status.value,
                    reason=f"Status query confirmed SUCCEEDED on attempt {current_attempt}",
                    actor="STATUS_WORKER",
                    at=now,
                )
            )
        elif status_result.status == "FAILED":
            new_status, _ = transition_payment(PaymentStatus.UNKNOWN, "status_failed")
            payment.status = new_status.value
            session.add(
                PaymentStatusHistory(
                    id=str(uuid.uuid4()),
                    payment_id=payment.id,
                    from_status=PaymentStatus.UNKNOWN.value,
                    to_status=new_status.value,
                    reason=f"Status query confirmed FAILED on attempt {current_attempt}",
                    actor="STATUS_WORKER",
                    at=now,
                )
            )
        else:
            # Still UNKNOWN
            if current_attempt >= settings.STATUS_QUERY_MAX_ATTEMPTS:
                payment.needs_review = True
                session.add(
                    PaymentStatusHistory(
                        id=str(uuid.uuid4()),
                        payment_id=payment.id,
                        from_status=PaymentStatus.UNKNOWN.value,
                        to_status=PaymentStatus.UNKNOWN.value,
                        reason=f"Status query exhausted {current_attempt} attempts: marked needs_review",
                        actor="STATUS_WORKER",
                        at=now,
                    )
                )
            else:
                session.add(
                    PaymentStatusHistory(
                        id=str(uuid.uuid4()),
                        payment_id=payment.id,
                        from_status=PaymentStatus.UNKNOWN.value,
                        to_status=PaymentStatus.UNKNOWN.value,
                        reason=f"Status query attempt {current_attempt} returned UNKNOWN",
                        actor="STATUS_WORKER",
                        at=now,
                    )
                )

        payment.updated_at = now
        await session.commit()
        await session.refresh(payment)
        return payment

