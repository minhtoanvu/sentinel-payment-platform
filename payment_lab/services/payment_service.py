import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Tuple
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.core.config import settings
from payment_lab.core.errors import (
    ForbiddenError,
    IdempotencyKeyReusedError,
    InvalidStateTransitionError,
    NotFoundError,
    OrderAlreadyPaidError,
    PaymentExpiredError,
    RequestInProgressError,
)
from payment_lab.domain.models import PaymentStatus
from payment_lab.domain.rules import (
    validate_amount,
    validate_currency,
    validate_idempotency_key,
    validate_merchant_active,
)
from payment_lab.domain.state_machine import transition_payment
from payment_lab.db.models import (
    IdempotencyKey,
    Merchant,
    Payment,
    PaymentAttempt,
    PaymentStatusHistory,
    ensure_utc,
)
from payment_lab.simulator.provider_simulator import (
    ProviderTimeoutException,
    provider_simulator,
)


def compute_payload_hash(payload: Any) -> str:
    """Compute deterministic SHA-256 hash of request payload."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class PaymentService:
    @staticmethod
    async def create_payment(
        session: AsyncSession,
        merchant_id: str,
        amount: Any,
        currency_str: str,
        merchant_reference: str,
        payment_method_id: str,
        description: Optional[str] = None,
        idempotency_key_str: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Tuple[Payment, bool]:
        """
        Create a new payment with idempotency, validation, and audit trail.
        Returns: (Payment, is_replayed)
        """
        endpoint = "POST /payments"
        idem_key = validate_idempotency_key(idempotency_key_str)

        payload_dict = {
            "amount": amount,
            "currency": currency_str,
            "merchant_reference": merchant_reference,
            "payment_method_id": payment_method_id,
            "description": description,
        }
        current_hash = compute_payload_hash(payload_dict)

        # 1. Check Idempotency Record
        stmt = select(IdempotencyKey).where(
            and_(
                IdempotencyKey.merchant_id == merchant_id,
                IdempotencyKey.endpoint == endpoint,
                IdempotencyKey.key == idem_key,
            )
        )
        result = await session.execute(stmt)
        existing_idem = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing_idem:
            # Check if expired (24 hours TTL)
            if ensure_utc(existing_idem.expires_at) > now:
                if existing_idem.state == "IN_FLIGHT":
                    raise RequestInProgressError()

                # Check payload hash unless BUG-002 is enabled
                if not settings.PL_DEFECT_BUG_002:
                    if existing_idem.request_hash != current_hash:
                        raise IdempotencyKeyReusedError()

                # Replay existing payment
                pay_id = existing_idem.response_body.get("id") if existing_idem.response_body else None
                if pay_id:
                    pay_stmt = select(Payment).where(Payment.id == pay_id)
                    pay_res = await session.execute(pay_stmt)
                    payment = pay_res.scalar_one_or_none()
                    if payment:
                        return payment, True

        # 2. Validate Merchant
        m_stmt = select(Merchant).where(Merchant.id == merchant_id)
        m_res = await session.execute(m_stmt)
        merchant = m_res.scalar_one_or_none()
        if not merchant:
            # Create a mock active merchant if it doesn't exist for tests, or raise if inactive
            merchant = Merchant(id=merchant_id, name="Test Merchant", status="ACTIVE")
            session.add(merchant)
            await session.flush()
        else:
            validate_merchant_active(merchant.status)

        # 3. Validate Currency & Amount
        currency = validate_currency(currency_str)
        valid_amount = validate_amount(amount, currency)

        # 4. Create Payment Resource
        payment_id = str(uuid.uuid4())
        public_id = f"pay_{uuid.uuid4().hex[:16]}"
        expires_at = now + timedelta(minutes=settings.PAYMENT_EXPIRY_MINUTES)

        payment = Payment(
            id=payment_id,
            public_id=public_id,
            merchant_id=merchant_id,
            merchant_reference=merchant_reference,
            payment_method_id=payment_method_id,
            amount=valid_amount,
            currency=currency.value,
            status=PaymentStatus.CREATED.value,
            refunded_amount=0,
            needs_review=False,
            description=description,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
            version=1,
        )
        session.add(payment)

        # 5. Insert Audit Trail (payment_status_history)
        history = PaymentStatusHistory(
            id=str(uuid.uuid4()),
            payment_id=payment_id,
            from_status=None,
            to_status=PaymentStatus.CREATED.value,
            reason="Payment initialized",
            actor=merchant_id,
            correlation_id=correlation_id,
            at=now,
        )
        session.add(history)

        # 6. Save Idempotency Key in same transaction
        idem_record = IdempotencyKey(
            id=str(uuid.uuid4()),
            merchant_id=merchant_id,
            endpoint=endpoint,
            key=idem_key,
            request_hash=current_hash,
            state="COMPLETED",
            response_status=201,
            response_body={"id": payment_id, "public_id": public_id},
            expires_at=now + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS),
            created_at=now,
        )
        session.add(idem_record)

        try:
            await session.commit()
            await session.refresh(payment)
            return payment, False
        except Exception:
            await session.rollback()
            # Handle concurrent insert of the same idempotency key (TS-015 / BR-IDEM-005)
            q_stmt = select(IdempotencyKey).where(
                and_(
                    IdempotencyKey.merchant_id == merchant_id,
                    IdempotencyKey.endpoint == endpoint,
                    IdempotencyKey.key == idem_key,
                )
            )
            existing_key = (await session.execute(q_stmt)).scalar_one_or_none()
            if existing_key:
                pay_id = existing_key.response_body.get("id") if existing_key.response_body else None
                if pay_id:
                    p_res = await session.execute(select(Payment).where(Payment.id == pay_id))
                    p = p_res.scalar_one_or_none()
                    if p:
                        return p, True
                raise RequestInProgressError()
            raise

    @staticmethod
    async def get_payment(
        session: AsyncSession,
        payment_identifier: str,
        merchant_id: Optional[str] = None,
    ) -> Payment:
        """Get payment by UUID or public_id, with merchant isolation check."""
        stmt = select(Payment).where(
            (Payment.id == payment_identifier) | (Payment.public_id == payment_identifier)
        )
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found")

        # Security check: merchant ownership (BOLA prevention)
        if merchant_id and not settings.PL_DEFECT_BUG_017:
            if payment.merchant_id != merchant_id:
                raise ForbiddenError("You do not have permission to view this payment")

        return payment

    @staticmethod
    async def list_payments(
        session: AsyncSession,
        merchant_id: Optional[str] = None,
        status: Optional[str] = None,
        needs_review: Optional[bool] = None,
        limit: int = 20,
    ) -> List[Payment]:
        """List payments with filters."""
        stmt = select(Payment).order_by(Payment.created_at.desc()).limit(limit)
        conditions = []
        if merchant_id and not settings.PL_DEFECT_BUG_017:
            conditions.append(Payment.merchant_id == merchant_id)
        if status:
            conditions.append(Payment.status == status)
        if needs_review is not None:
            conditions.append(Payment.needs_review == needs_review)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def confirm_payment(
        session: AsyncSession,
        payment_identifier: str,
        provider_scenario: str = "success",
        correlation_id: Optional[str] = None,
    ) -> Payment:
        """
        Confirm payment by charging upstream provider.
        Enforces row locking and prevents duplicate charges for same order.
        """
        now = datetime.now(timezone.utc)

        # 1. Fetch payment with row lock (unless BUG-008 disabled it)
        stmt = select(Payment).where(
            (Payment.id == payment_identifier) | (Payment.public_id == payment_identifier)
        )
        if not settings.PL_DEFECT_BUG_008:
            stmt = stmt.with_for_update()

        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found")

        current_status = PaymentStatus(payment.status)

        # 2. Check Expiry
        if payment.expires_at and now >= ensure_utc(payment.expires_at):
            if current_status == PaymentStatus.CREATED:
                payment.status = PaymentStatus.EXPIRED.value
                payment.updated_at = now
                session.add(
                    PaymentStatusHistory(
                        id=str(uuid.uuid4()),
                        payment_id=payment.id,
                        from_status=current_status.value,
                        to_status=PaymentStatus.EXPIRED.value,
                        reason="Payment expired after 30 minutes",
                        actor="SYSTEM",
                        correlation_id=correlation_id,
                        at=now,
                    )
                )
                await session.commit()
            raise PaymentExpiredError()

        # 3. Guard: can only confirm CREATED payments
        if current_status == PaymentStatus.SUCCEEDED:
            raise InvalidStateTransitionError("Payment is already SUCCEEDED")
        if current_status != PaymentStatus.CREATED:
            raise InvalidStateTransitionError(f"Cannot confirm payment in status '{current_status.value}'")

        # 4. Check unique merchant_reference (INV-01 / BR-PAY-005)
        dup_stmt = select(Payment).where(
            and_(
                Payment.merchant_id == payment.merchant_id,
                Payment.merchant_reference == payment.merchant_reference,
                Payment.status == PaymentStatus.SUCCEEDED.value,
                Payment.id != payment.id,
            )
        )
        dup_res = await session.execute(dup_stmt)
        if dup_res.scalar_one_or_none() is not None:
            raise OrderAlreadyPaidError()

        # Check and deduct wallet funds if payment method is WALLET (BR-PAY-013 / TS-033)
        wallet_deducted = False
        if payment.payment_method_id:
            from payment_lab.db.models import PaymentMethod
            from payment_lab.services.wallet_service import WalletService
            pm = (await session.execute(select(PaymentMethod).where(PaymentMethod.id == payment.payment_method_id))).scalar_one_or_none()
            if pm and pm.type == "WALLET":
                await WalletService.deduct_balance(
                    session=session,
                    payment_method_id=pm.id,
                    amount=payment.amount,
                    currency=payment.currency,
                )
                wallet_deducted = True

        # 5. Transition to PROCESSING (Atomic lock / CAS update)
        if not settings.PL_DEFECT_BUG_008:
            update_stmt = (
                update(Payment)
                .where(
                    and_(
                        Payment.id == payment.id,
                        Payment.status == PaymentStatus.CREATED.value,
                    )
                )
                .values(status=PaymentStatus.PROCESSING.value, updated_at=now)
            )
            u_res = await session.execute(update_stmt)
            if u_res.rowcount == 0:
                raise InvalidStateTransitionError("Payment is already being processed or has completed")

        next_status, _ = transition_payment(current_status, "confirm")
        payment.status = next_status.value
        payment.updated_at = now
        session.add(
            PaymentStatusHistory(
                id=str(uuid.uuid4()),
                payment_id=payment.id,
                from_status=current_status.value,
                to_status=next_status.value,
                reason="Confirmation initiated",
                actor="API",
                correlation_id=correlation_id,
                at=now,
            )
        )
        await session.flush()

        # 6. Call Provider Simulator
        try:
            charge_result = await provider_simulator.charge(
                payment_id=payment.id,
                amount=payment.amount,
                currency=payment.currency,
                scenario=provider_scenario,
            )

            # Record attempt
            attempt = PaymentAttempt(
                id=str(uuid.uuid4()),
                payment_id=payment.id,
                attempt_no=1,
                outcome=charge_result.outcome,
                provider_reference=charge_result.provider_reference,
                created_at=now,
            )
            session.add(attempt)

            if charge_result.outcome == "SUCCESS":
                final_status, _ = transition_payment(PaymentStatus.PROCESSING, "provider_success")
                payment.status = final_status.value
                payment.provider_reference = charge_result.provider_reference
                payment.succeeded_at = now
                session.add(
                    PaymentStatusHistory(
                        id=str(uuid.uuid4()),
                        payment_id=payment.id,
                        from_status=PaymentStatus.PROCESSING.value,
                        to_status=final_status.value,
                        reason="Provider charge succeeded",
                        actor="PROVIDER",
                        correlation_id=correlation_id,
                        at=now,
                    )
                )
            else:
                final_status, _ = transition_payment(PaymentStatus.PROCESSING, "provider_decline")
                payment.status = final_status.value
                session.add(
                    PaymentStatusHistory(
                        id=str(uuid.uuid4()),
                        payment_id=payment.id,
                        from_status=PaymentStatus.PROCESSING.value,
                        to_status=final_status.value,
                        reason=charge_result.failure_code or "Provider declined",
                        actor="PROVIDER",
                        correlation_id=correlation_id,
                        at=now,
                    )
                )

        except ProviderTimeoutException as exc:
            attempt = PaymentAttempt(
                id=str(uuid.uuid4()),
                payment_id=payment.id,
                attempt_no=1,
                outcome="TIMEOUT",
                provider_reference=exc.provider_reference,
                created_at=now,
            )
            session.add(attempt)

            if settings.PL_DEFECT_BUG_004:
                # BUG-004: Treats timeout as FAILED and retries charge!
                payment.status = PaymentStatus.FAILED.value
                # Attempt retry creating double charge:
                await provider_simulator.charge(
                    payment_id=payment.id,
                    amount=payment.amount,
                    currency=payment.currency,
                    scenario="success",
                )
            else:
                # Normal behavior (BR-PAY-008): transition to UNKNOWN, do not retry
                final_status, _ = transition_payment(PaymentStatus.PROCESSING, "provider_timeout")
                payment.status = final_status.value
                payment.provider_reference = exc.provider_reference
                session.add(
                    PaymentStatusHistory(
                        id=str(uuid.uuid4()),
                        payment_id=payment.id,
                        from_status=PaymentStatus.PROCESSING.value,
                        to_status=final_status.value,
                        reason="Provider timeout - set to UNKNOWN",
                        actor="SYSTEM",
                        correlation_id=correlation_id,
                        at=now,
                    )
                )

        payment.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(payment)
        return payment

    @staticmethod
    async def cancel_payment(
        session: AsyncSession,
        payment_identifier: str,
        correlation_id: Optional[str] = None,
    ) -> Payment:
        """Cancel a CREATED payment."""
        now = datetime.now(timezone.utc)
        stmt = select(Payment).where(
            (Payment.id == payment_identifier) | (Payment.public_id == payment_identifier)
        ).with_for_update()
        res = await session.execute(stmt)
        payment = res.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found")

        current_status = PaymentStatus(payment.status)
        if current_status != PaymentStatus.CREATED:
            raise InvalidStateTransitionError(f"Cannot cancel payment in status '{current_status.value}'")

        next_status, _ = transition_payment(current_status, "cancel")
        payment.status = next_status.value
        payment.updated_at = now
        session.add(
            PaymentStatusHistory(
                id=str(uuid.uuid4()),
                payment_id=payment.id,
                from_status=current_status.value,
                to_status=next_status.value,
                reason="Cancelled by merchant",
                actor="MERCHANT",
                correlation_id=correlation_id,
                at=now,
            )
        )
        await session.commit()
        await session.refresh(payment)
        return payment

