import pytest
from payment_lab.core.errors import InvalidStateTransitionError
from payment_lab.domain.models import PaymentStatus, RefundStatus
from payment_lab.domain.state_machine import (
    PAYMENT_TRANSITIONS,
    REFUND_TRANSITIONS,
    transition_payment,
    transition_refund,
)


class TestPaymentStateMachine:
    """TS-024: Complete (state x event) matrix verification."""

    @pytest.mark.parametrize(
        "current_status, event, expected_next",
        [
            (PaymentStatus.CREATED, "confirm", PaymentStatus.PROCESSING),
            (PaymentStatus.CREATED, "cancel", PaymentStatus.CANCELED),
            (PaymentStatus.CREATED, "expire", PaymentStatus.EXPIRED),
            (PaymentStatus.PROCESSING, "provider_success", PaymentStatus.SUCCEEDED),
            (PaymentStatus.PROCESSING, "provider_decline", PaymentStatus.FAILED),
            (PaymentStatus.PROCESSING, "provider_timeout", PaymentStatus.UNKNOWN),
            (PaymentStatus.UNKNOWN, "status_success", PaymentStatus.SUCCEEDED),
            (PaymentStatus.UNKNOWN, "status_failed", PaymentStatus.FAILED),
            (PaymentStatus.UNKNOWN, "status_unknown", PaymentStatus.UNKNOWN),
        ],
    )
    def test_valid_payment_transitions(self, current_status, event, expected_next):
        next_status, anomaly = transition_payment(current_status, event)
        assert next_status == expected_next
        assert anomaly is None

    @pytest.mark.parametrize(
        "current_status, event",
        [
            (PaymentStatus.SUCCEEDED, "confirm"),
            (PaymentStatus.SUCCEEDED, "cancel"),
            (PaymentStatus.SUCCEEDED, "provider_decline"),
            (PaymentStatus.FAILED, "confirm"),
            (PaymentStatus.FAILED, "status_success"),
            (PaymentStatus.CANCELED, "confirm"),
            (PaymentStatus.EXPIRED, "confirm"),
            (PaymentStatus.CREATED, "status_success"),
            (PaymentStatus.PROCESSING, "cancel"),  # Cannot cancel while processing
        ],
    )
    def test_invalid_payment_transitions(self, current_status, event):
        with pytest.raises(InvalidStateTransitionError):
            transition_payment(current_status, event)

    def test_late_conflicting_webhook_on_terminal_records_anomaly(self):
        # TS-030: Late webhook SUCCEEDED after FAILED keeps FAILED and emits STATE_CONFLICT anomaly
        status, anomaly = transition_payment(
            PaymentStatus.FAILED, "provider_success", is_late_webhook=True
        )
        assert status == PaymentStatus.FAILED
        assert anomaly == "STATE_CONFLICT"


class TestRefundStateMachine:
    @pytest.mark.parametrize(
        "current_status, event, expected_next",
        [
            (RefundStatus.PENDING_APPROVAL, "approve", RefundStatus.REQUESTED),
            (RefundStatus.PENDING_APPROVAL, "reject", RefundStatus.REJECTED),
            (RefundStatus.REQUESTED, "process", RefundStatus.PROCESSING),
            (RefundStatus.PROCESSING, "provider_success", RefundStatus.SUCCEEDED),
            (RefundStatus.PROCESSING, "provider_decline", RefundStatus.FAILED),
            (RefundStatus.PROCESSING, "provider_timeout", RefundStatus.UNKNOWN),
            (RefundStatus.UNKNOWN, "status_success", RefundStatus.SUCCEEDED),
            (RefundStatus.UNKNOWN, "status_failed", RefundStatus.FAILED),
        ],
    )
    def test_valid_refund_transitions(self, current_status, event, expected_next):
        assert transition_refund(current_status, event) == expected_next

    @pytest.mark.parametrize(
        "current_status, event",
        [
            (RefundStatus.SUCCEEDED, "approve"),
            (RefundStatus.FAILED, "process"),
            (RefundStatus.REJECTED, "approve"),
        ],
    )
    def test_invalid_refund_transitions(self, current_status, event):
        with pytest.raises(InvalidStateTransitionError):
            transition_refund(current_status, event)

