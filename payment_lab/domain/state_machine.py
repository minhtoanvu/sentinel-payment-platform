from typing import Optional, Tuple
from payment_lab.core.config import settings
from payment_lab.core.errors import InvalidStateTransitionError
from payment_lab.domain.models import PaymentStatus, RefundStatus


# Valid payment transitions mapping: (current_status, event) -> next_status
PAYMENT_TRANSITIONS: dict[Tuple[PaymentStatus, str], PaymentStatus] = {
    (PaymentStatus.CREATED, "confirm"): PaymentStatus.PROCESSING,
    (PaymentStatus.CREATED, "cancel"): PaymentStatus.CANCELED,
    (PaymentStatus.CREATED, "expire"): PaymentStatus.EXPIRED,
    (PaymentStatus.PROCESSING, "provider_success"): PaymentStatus.SUCCEEDED,
    (PaymentStatus.PROCESSING, "provider_decline"): PaymentStatus.FAILED,
    (PaymentStatus.PROCESSING, "provider_timeout"): PaymentStatus.UNKNOWN,
    (PaymentStatus.UNKNOWN, "status_success"): PaymentStatus.SUCCEEDED,
    (PaymentStatus.UNKNOWN, "status_failed"): PaymentStatus.FAILED,
    (PaymentStatus.UNKNOWN, "status_unknown"): PaymentStatus.UNKNOWN,
}


def transition_payment(
    current_status: PaymentStatus,
    event: str,
    is_late_webhook: bool = False,
) -> Tuple[PaymentStatus, Optional[str]]:
    """
    Execute state transition for Payment.
    Returns: (new_status, anomaly_code)
    Raises InvalidStateTransitionError if transition is not permitted.
    """
    # Special case: late webhook conflicting with terminal status
    if current_status.is_terminal and is_late_webhook:
        if settings.PL_DEFECT_BUG_011:
            # BUG-011: Late webhook improperly overwrites terminal status!
            if event == "provider_success":
                return PaymentStatus.SUCCEEDED, None
            elif event == "provider_decline":
                return PaymentStatus.FAILED, None
        # Normal behavior (BR-PAY-014, BR-WH-006): keep terminal status, record STATE_CONFLICT anomaly
        return current_status, "STATE_CONFLICT"

    # Terminal state rejection
    if current_status.is_terminal:
        raise InvalidStateTransitionError(
            f"Cannot transition payment from terminal status '{current_status.value}' via event '{event}'"
        )

    key = (current_status, event)
    if key not in PAYMENT_TRANSITIONS:
        raise InvalidStateTransitionError(
            f"Invalid payment state transition from '{current_status.value}' with event '{event}'"
        )

    return PAYMENT_TRANSITIONS[key], None


# Valid refund transitions mapping: (current_status, event) -> next_status
REFUND_TRANSITIONS: dict[Tuple[RefundStatus, str], RefundStatus] = {
    (RefundStatus.PENDING_APPROVAL, "approve"): RefundStatus.REQUESTED,
    (RefundStatus.PENDING_APPROVAL, "reject"): RefundStatus.REJECTED,
    (RefundStatus.REQUESTED, "process"): RefundStatus.PROCESSING,
    (RefundStatus.PROCESSING, "provider_success"): RefundStatus.SUCCEEDED,
    (RefundStatus.PROCESSING, "provider_decline"): RefundStatus.FAILED,
    (RefundStatus.PROCESSING, "provider_timeout"): RefundStatus.UNKNOWN,
    (RefundStatus.UNKNOWN, "status_success"): RefundStatus.SUCCEEDED,
    (RefundStatus.UNKNOWN, "status_failed"): RefundStatus.FAILED,
}


def transition_refund(current_status: RefundStatus, event: str) -> RefundStatus:
    """
    Execute state transition for Refund.
    Raises InvalidStateTransitionError if transition is not permitted.
    """
    if current_status.is_terminal:
        raise InvalidStateTransitionError(
            f"Cannot transition refund from terminal status '{current_status.value}' via event '{event}'"
        )

    key = (current_status, event)
    if key not in REFUND_TRANSITIONS:
        raise InvalidStateTransitionError(
            f"Invalid refund state transition from '{current_status.value}' with event '{event}'"
        )

    return REFUND_TRANSITIONS[key]

