import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.core.config import settings
from payment_lab.core.errors import (
    InvalidSignatureError,
    WebhookTimestampOutOfRangeError,
)
from payment_lab.domain.models import PaymentStatus, WebhookProcessingStatus, WebhookVerificationStatus
from payment_lab.domain.state_machine import transition_payment
from payment_lab.db.models import Payment, PaymentStatusHistory, WebhookEvent
from payment_lab.simulator.provider_simulator import provider_simulator


class WebhookService:
    @staticmethod
    async def process_webhook(
        session: AsyncSession,
        provider: str,
        payload_bytes: bytes,
        payload_dict: dict[str, Any],
        signature_header: Optional[str],
        timestamp_header: Optional[str],
        mock_now_ts: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Process upstream webhook event.
        Returns: dict(status, event_id, deduplicated, processing_status)
        """
        now = datetime.now(timezone.utc)
        event_id = payload_dict.get("event_id") or str(uuid.uuid4())
        event_type = payload_dict.get("event_type", "unknown")
        provider_seq = payload_dict.get("provider_sequence")

        # 1. Signature & Timestamp Verification
        is_verified = provider_simulator.verify_signature(
            timestamp_str=timestamp_header,
            signature=signature_header,
            payload_bytes=payload_bytes,
            now_ts=mock_now_ts,
        )

        if not is_verified:
            # Check existing event to avoid UNIQUE constraint violation on repeated bad deliveries
            ev_stmt = select(WebhookEvent).where(
                and_(WebhookEvent.provider == provider, WebhookEvent.event_id == event_id)
            )
            existing_bad = (await session.execute(ev_stmt)).scalar_one_or_none()
            if not existing_bad:
                session.add(
                    WebhookEvent(
                        id=str(uuid.uuid4()),
                        provider=provider,
                        event_id=event_id,
                        event_type=event_type,
                        provider_sequence=provider_seq,
                        verification_status=WebhookVerificationStatus.FAILED.value,
                        processing_status=WebhookProcessingStatus.FAILED.value,
                        raw_payload=payload_dict,
                        received_at=now,
                    )
                )
                await session.commit()

            # Check if failure is due to timestamp or bad signature
            if timestamp_header and not settings.PL_DEFECT_BUG_006:
                try:
                    ts = int(timestamp_header)
                    curr = mock_now_ts if mock_now_ts is not None else int(now.timestamp())
                    if abs(curr - ts) > settings.WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
                        raise WebhookTimestampOutOfRangeError()
                except ValueError:
                    pass

            raise InvalidSignatureError()

        # 2. Check Deduplication by (provider, event_id) (BR-WH-003 / INV-08)
        stmt = select(WebhookEvent).where(
            and_(
                WebhookEvent.provider == provider,
                WebhookEvent.event_id == event_id,
            )
        )
        result = await session.execute(stmt)
        existing_event = result.scalar_one_or_none()

        if existing_event and not settings.PL_DEFECT_BUG_003:
            # Normal: deduplicate and return 200 without second side effects
            return {
                "status": "acknowledged",
                "event_id": event_id,
                "deduplicated": True,
                "processing_status": existing_event.processing_status,
            }

        # 3. Store Event
        webhook_event = WebhookEvent(
            id=str(uuid.uuid4()),
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            provider_sequence=provider_seq,
            verification_status=WebhookVerificationStatus.VERIFIED.value,
            processing_status=WebhookProcessingStatus.RECEIVED.value,
            raw_payload=payload_dict,
            received_at=now,
        )
        session.add(webhook_event)
        try:
            await session.flush()
        except Exception:
            await session.rollback()
            # Concurrent insertion of same (provider, event_id) -> treat as deduplicated (INV-08)
            return {
                "status": "acknowledged",
                "event_id": event_id,
                "deduplicated": True,
                "processing_status": WebhookProcessingStatus.PROCESSED.value,
            }

        # 4. Handle Event Processing
        processing_status = WebhookProcessingStatus.PROCESSED.value
        data = payload_dict.get("data", {})
        provider_ref = data.get("provider_reference")
        payment_id = data.get("payment_id")

        if event_type not in ("payment.succeeded", "payment.failed"):
            processing_status = WebhookProcessingStatus.IGNORED.value
        else:
            # Find Payment
            p_stmt = select(Payment).where(
                (Payment.provider_reference == provider_ref)
                | (Payment.id == payment_id)
                | (Payment.public_id == payment_id)
            ).with_for_update()
            p_res = await session.execute(p_stmt)
            payment = p_res.scalar_one_or_none()

            if not payment:
                processing_status = WebhookProcessingStatus.ORPHAN.value
            else:
                current_status = PaymentStatus(payment.status)
                event_name = "provider_success" if event_type == "payment.succeeded" else "provider_decline"

                if current_status.is_terminal:
                    # Terminal state handling
                    if (current_status == PaymentStatus.SUCCEEDED and event_type == "payment.succeeded") or (
                        current_status == PaymentStatus.FAILED and event_type == "payment.failed"
                    ):
                        # Idempotent terminal confirmation
                        pass
                    else:
                        # Conflicting late webhook
                        if settings.PL_DEFECT_BUG_011:
                            # BUG-011: Defect improperly overwrites terminal status!
                            new_st = PaymentStatus.SUCCEEDED if event_type == "payment.succeeded" else PaymentStatus.FAILED
                            payment.status = new_st.value
                        else:
                            # Normal (BR-PAY-014, BR-WH-006): do not overwrite, log STATE_CONFLICT anomaly
                            session.add(
                                PaymentStatusHistory(
                                    id=str(uuid.uuid4()),
                                    payment_id=payment.id,
                                    from_status=current_status.value,
                                    to_status=current_status.value,
                                    reason=f"Anomaly STATE_CONFLICT: Late webhook {event_type} ignored",
                                    actor="WEBHOOK",
                                    at=now,
                                )
                            )
                else:
                    # If payment was in CREATED status, transition to PROCESSING first
                    if current_status == PaymentStatus.CREATED:
                        proc_status, _ = transition_payment(current_status, "confirm")
                        session.add(
                            PaymentStatusHistory(
                                id=str(uuid.uuid4()),
                                payment_id=payment.id,
                                from_status=current_status.value,
                                to_status=proc_status.value,
                                reason="Auto-transitioned to PROCESSING upon provider webhook",
                                actor="WEBHOOK",
                                at=now,
                            )
                        )
                        current_status = proc_status

                    # Valid transition from PROCESSING / UNKNOWN
                    next_status, _ = transition_payment(current_status, event_name, is_late_webhook=False)
                    payment.status = next_status.value
                    if next_status == PaymentStatus.SUCCEEDED and not payment.succeeded_at:
                        payment.succeeded_at = now

                    session.add(
                        PaymentStatusHistory(
                            id=str(uuid.uuid4()),
                            payment_id=payment.id,
                            from_status=current_status.value,
                            to_status=next_status.value,
                            reason=f"Updated by webhook {event_type}",
                            actor="WEBHOOK",
                            at=now,
                        )
                    )

        webhook_event.processing_status = processing_status
        await session.commit()

        return {
            "status": "acknowledged",
            "event_id": event_id,
            "deduplicated": False,
            "processing_status": processing_status,
        }
