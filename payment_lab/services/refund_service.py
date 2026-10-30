import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Tuple
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.core.config import settings
from payment_lab.core.errors import (
    IdempotencyKeyReusedError,
    NotFoundError,
    PaymentNotRefundableError,
    RefundCurrencyMismatchError,
    RefundExceedsRefundableError,
    RefundLimitReachedError,
    RefundWindowExpiredError,
    RequestInProgressError,
    SelfApprovalNotAllowedError,
    ValidationError,
)
from payment_lab.domain.invariants import assert_inv_02_refund_never_exceeds_amount
from payment_lab.domain.models import Currency, PaymentStatus, RefundStatus
from payment_lab.domain.rules import validate_amount, validate_currency, validate_idempotency_key
from payment_lab.domain.state_machine import transition_refund
from payment_lab.db.models import IdempotencyKey, Payment, Refund, RefundStatusHistory, ensure_utc
from payment_lab.services.payment_service import compute_payload_hash
from payment_lab.simulator.provider_simulator import (
    ProviderTimeoutException,
    provider_simulator,
)


class RefundService:
    @staticmethod
    async def create_refund(
        session: AsyncSession,
        payment_identifier: str,
        amount: Any,
        currency_str: str,
        reason: Optional[str] = None,
        created_by: str = "merchant_user",
        idempotency_key_str: Optional[str] = None,
        provider_scenario: str = "success",
    ) -> Tuple[Refund, bool, int]:
        """
        Create refund for a payment.
        Returns: (Refund, is_replayed, remaining_refundable)
        """
        now = datetime.now(timezone.utc)
        endpoint = f"POST /payments/{payment_identifier}/refunds"
        idem_key = validate_idempotency_key(idempotency_key_str)

        payload_dict = {"amount": amount, "currency": currency_str, "reason": reason}
        current_hash = compute_payload_hash(payload_dict)

        # 1. Fetch payment with row lock
        stmt = select(Payment).where(
            (Payment.id == payment_identifier) | (Payment.public_id == payment_identifier)
        ).with_for_update()
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found")

        # 2. Check Idempotency Record
        idem_stmt = select(IdempotencyKey).where(
            and_(
                IdempotencyKey.merchant_id == payment.merchant_id,
                IdempotencyKey.endpoint == endpoint,
                IdempotencyKey.key == idem_key,
            )
        )
        idem_res = await session.execute(idem_stmt)
        existing_idem = idem_res.scalar_one_or_none()

        if existing_idem:
            if ensure_utc(existing_idem.expires_at) > now:
                if existing_idem.state == "IN_FLIGHT":
                    raise RequestInProgressError()

                if not settings.PL_DEFECT_BUG_002 and existing_idem.request_hash != current_hash:
                    raise IdempotencyKeyReusedError()

                ref_id = existing_idem.response_body.get("id") if existing_idem.response_body else None
                if ref_id:
                    ref_stmt = select(Refund).where(Refund.id == ref_id)
                    ref_r = await session.execute(ref_stmt)
                    refund = ref_r.scalar_one_or_none()
                    if refund:
                        refundable = await RefundService.calculate_refundable_amount(session, payment.id)
                        return refund, True, refundable

        # 3. Guard: Payment must be SUCCEEDED
        if payment.status != PaymentStatus.SUCCEEDED.value:
            raise PaymentNotRefundableError(
                f"Cannot refund payment in status '{payment.status}'. Must be SUCCEEDED."
            )

        # 4. Currency check
        currency = validate_currency(currency_str)
        if currency.value != payment.currency:
            raise RefundCurrencyMismatchError(
                f"Refund currency '{currency.value}' does not match payment currency '{payment.currency}'"
            )

        # Validate amount type & positivity
        if type(amount) is not int or amount <= 0:
            raise ValidationError(
                message="Refund amount must be a positive integer",
                details=[{"field": "amount", "issue": "Invalid refund amount"}],
            )

        # 5. Check 180-day Refund Window (BR-REF-005)
        if payment.succeeded_at:
            delta = now - ensure_utc(payment.succeeded_at)
            days_elapsed = delta.total_seconds() / 86400.0

            if settings.PL_DEFECT_BUG_012:
                # BUG-012: Rejects day 180 (boundary off-by-one: rejects >= 180)
                if days_elapsed >= 180.0:
                    raise RefundWindowExpiredError()
            else:
                # Normal: only reject if strictly > 180 days
                if days_elapsed > 180.0:
                    raise RefundWindowExpiredError()

        # 6. Check Refund Count Limit (max 10 active refunds) (BR-REF-004)
        count_stmt = select(func.count(Refund.id)).where(
            and_(
                Refund.payment_id == payment.id,
                Refund.status.notin_([RefundStatus.FAILED.value, RefundStatus.REJECTED.value]),
            )
        )
        count_res = await session.execute(count_stmt)
        active_count = count_res.scalar_one() or 0
        if active_count >= settings.MAX_REFUNDS_PER_PAYMENT:
            raise RefundLimitReachedError()

        # 7. Calculate remaining refundable
        refundable = await RefundService.calculate_refundable_amount(session, payment.id)

        # Check amount vs refundable: BUG-001 defect checks '<' instead of '<='
        if settings.PL_DEFECT_BUG_001:
            if amount >= refundable:
                raise RefundExceedsRefundableError(
                    f"Refund amount {amount} exceeds remaining refundable {refundable}"
                )
        else:
            if amount > refundable:
                raise RefundExceedsRefundableError(
                    f"Refund amount {amount} exceeds remaining refundable {refundable}"
                )

        # 8. Check Maker-Checker Threshold
        threshold = (
            settings.REFUND_APPROVAL_THRESHOLD_VND
            if payment.currency == Currency.VND.value
            else settings.REFUND_APPROVAL_THRESHOLD_USD_CENTS
        )
        needs_approval = amount >= threshold

        # Atomic reservation BEFORE adding refund object to session (INV-02)
        if not needs_approval and not settings.PL_DEFECT_BUG_005:
            u_stmt = (
                update(Payment)
                .where(
                    and_(
                        Payment.id == payment.id,
                        Payment.refunded_amount + amount <= Payment.amount,
                    )
                )
                .values(refunded_amount=Payment.refunded_amount + amount)
            )
            u_res = await session.execute(u_stmt)
            if u_res.rowcount == 0:
                raise RefundExceedsRefundableError(
                    f"Refund amount {amount} exceeds remaining refundable amount"
                )

        refund_id = str(uuid.uuid4())
        public_id = f"ref_{uuid.uuid4().hex[:16]}"
        initial_status = RefundStatus.PENDING_APPROVAL if needs_approval else RefundStatus.REQUESTED

        refund = Refund(
            id=refund_id,
            public_id=public_id,
            payment_id=payment.id,
            amount=amount,
            currency=currency.value,
            status=initial_status.value,
            reason=reason,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        session.add(refund)

        session.add(
            RefundStatusHistory(
                id=str(uuid.uuid4()),
                refund_id=refund_id,
                from_status=None,
                to_status=initial_status.value,
                at=now,
            )
        )

        # If approval not required, execute charge refund with provider
        if not needs_approval:
            refund.status = RefundStatus.PROCESSING.value
            try:
                prov_res = await provider_simulator.refund(
                    provider_reference=payment.provider_reference or "sim_ref",
                    amount=amount,
                    currency=currency.value,
                    scenario=provider_scenario,
                )
                refund.provider_reference = prov_res.provider_reference
                if prov_res.outcome == "SUCCESS":
                    refund.status = RefundStatus.SUCCEEDED.value
                    if settings.PL_DEFECT_BUG_005:
                        payment.refunded_amount += amount
                    assert_inv_02_refund_never_exceeds_amount(payment.refunded_amount, payment.amount)
                else:
                    refund.status = RefundStatus.FAILED.value
                    if not settings.PL_DEFECT_BUG_005:
                        await session.execute(
                            update(Payment)
                            .where(Payment.id == payment.id)
                            .values(refunded_amount=Payment.refunded_amount - amount)
                        )
            except ProviderTimeoutException as exc:
                refund.status = RefundStatus.UNKNOWN.value
                refund.provider_reference = exc.provider_reference

            session.add(
                RefundStatusHistory(
                    id=str(uuid.uuid4()),
                    refund_id=refund_id,
                    from_status=RefundStatus.PROCESSING.value,
                    to_status=refund.status,
                    at=datetime.now(timezone.utc),
                )
            )

        # Save idempotency record
        idem_record = IdempotencyKey(
            id=str(uuid.uuid4()),
            merchant_id=payment.merchant_id,
            endpoint=endpoint,
            key=idem_key,
            request_hash=current_hash,
            state="COMPLETED",
            response_status=201,
            response_body={"id": refund_id, "public_id": public_id},
            expires_at=now + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS),
            created_at=now,
        )
        session.add(idem_record)

        await session.commit()
        await session.refresh(refund)
        await session.refresh(payment)

        remaining = await RefundService.calculate_refundable_amount(session, payment.id)
        return refund, False, remaining

    @staticmethod
    async def approve_refund(
        session: AsyncSession,
        refund_identifier: str,
        approved_by: str,
    ) -> Refund:
        """Approve a PENDING_APPROVAL refund (Maker-Checker BR-REF-007)."""
        now = datetime.now(timezone.utc)
        stmt = select(Refund).where(
            (Refund.id == refund_identifier) | (Refund.public_id == refund_identifier)
        ).with_for_update()
        res = await session.execute(stmt)
        refund = res.scalar_one_or_none()
        if not refund:
            raise NotFoundError("Refund not found")

        if refund.status != RefundStatus.PENDING_APPROVAL.value:
            raise ValidationError("Refund is not in PENDING_APPROVAL status")

        # Maker-checker policy: creator cannot approve their own refund
        if refund.created_by == approved_by:
            raise SelfApprovalNotAllowedError()

        refund.approved_by = approved_by
        refund.status = RefundStatus.REQUESTED.value
        refund.updated_at = now

        session.add(
            RefundStatusHistory(
                id=str(uuid.uuid4()),
                refund_id=refund.id,
                from_status=RefundStatus.PENDING_APPROVAL.value,
                to_status=RefundStatus.REQUESTED.value,
                at=now,
            )
        )

        # Execute refund with provider
        refund.status = RefundStatus.PROCESSING.value
        try:
            prov_res = await provider_simulator.refund(
                provider_reference=refund.provider_reference or "sim_ref",
                amount=refund.amount,
                currency=refund.currency,
            )
            refund.provider_reference = prov_res.provider_reference
            if prov_res.outcome == "SUCCESS":
                refund.status = RefundStatus.SUCCEEDED.value
                # Update payment refunded_amount
                p_stmt = select(Payment).where(Payment.id == refund.payment_id).with_for_update()
                p_res = await session.execute(p_stmt)
                payment = p_res.scalar_one()
                payment.refunded_amount += refund.amount
            else:
                refund.status = RefundStatus.FAILED.value
        except ProviderTimeoutException as exc:
            refund.status = RefundStatus.UNKNOWN.value
            refund.provider_reference = exc.provider_reference

        session.add(
            RefundStatusHistory(
                id=str(uuid.uuid4()),
                refund_id=refund.id,
                from_status=RefundStatus.PROCESSING.value,
                to_status=refund.status,
                at=now,
            )
        )

        await session.commit()
        await session.refresh(refund)
        return refund

    @staticmethod
    async def calculate_refundable_amount(session: AsyncSession, payment_id: str) -> int:
        """
        Calculate remaining refundable amount.
        refundable = payment.amount - sum(succeeded) - sum(pending_approval, requested, processing, unknown)
        """
        stmt = select(Payment).where(Payment.id == payment_id)
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            return 0

        # Query all refunds for this payment
        ref_stmt = select(Refund).where(Refund.payment_id == payment_id)
        ref_res = await session.execute(ref_stmt)
        refunds = ref_res.scalars().all()

        succeeded_total = 0
        reservation_total = 0

        for r in refunds:
            status = RefundStatus(r.status)
            if status == RefundStatus.SUCCEEDED:
                succeeded_total += r.amount
            elif status.is_reservation:
                # BUG-005 check: defect ignores reservation of PROCESSING/UNKNOWN refunds!
                if not settings.PL_DEFECT_BUG_005:
                    reservation_total += r.amount

        refundable = payment.amount - succeeded_total - reservation_total
        return max(0, refundable)

