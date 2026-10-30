from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class Currency(str, Enum):
    VND = "VND"
    USD = "USD"


class PaymentStatus(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    UNKNOWN = "UNKNOWN"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"

    @classmethod
    def terminal_statuses(cls) -> set["PaymentStatus"]:
        return {cls.SUCCEEDED, cls.FAILED, cls.CANCELED, cls.EXPIRED}

    @property
    def is_terminal(self) -> bool:
        return self in (
            PaymentStatus.SUCCEEDED,
            PaymentStatus.FAILED,
            PaymentStatus.CANCELED,
            PaymentStatus.EXPIRED,
        )


class RefundStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REQUESTED = "REQUESTED"
    PROCESSING = "PROCESSING"
    UNKNOWN = "UNKNOWN"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"

    @property
    def is_reservation(self) -> bool:
        """Statuses that hold refundable reservation amount."""
        return self in (
            RefundStatus.PENDING_APPROVAL,
            RefundStatus.REQUESTED,
            RefundStatus.PROCESSING,
            RefundStatus.UNKNOWN,
        )

    @property
    def is_terminal(self) -> bool:
        return self in (RefundStatus.SUCCEEDED, RefundStatus.FAILED, RefundStatus.REJECTED)


class PaymentMethodType(str, Enum):
    CARD_TOKEN = "CARD_TOKEN"
    WALLET = "WALLET"


class MerchantStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class IdempotencyState(str, Enum):
    IN_FLIGHT = "IN_FLIGHT"
    COMPLETED = "COMPLETED"


class WebhookVerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class WebhookProcessingStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    IGNORED = "IGNORED"
    STALE = "STALE"
    ORPHAN = "ORPHAN"
    FAILED = "FAILED"


class MismatchType(str, Enum):
    MISSING_IN_PROVIDER = "MISSING_IN_PROVIDER"
    MISSING_IN_INTERNAL = "MISSING_IN_INTERNAL"
    DUPLICATE_IN_PROVIDER = "DUPLICATE_IN_PROVIDER"
    DUPLICATE_IN_INTERNAL = "DUPLICATE_IN_INTERNAL"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    STATUS_MISMATCH = "STATUS_MISMATCH"
    CUTOFF_TIMING_DIFF = "CUTOFF_TIMING_DIFF"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    WRITTEN_OFF = "WRITTEN_OFF"


# Pydantic Schemas for API Requests & Responses

class CreatePaymentRequest(BaseModel):
    amount: int
    currency: str
    merchant_reference: str = Field(..., max_length=64)
    payment_method_id: str
    description: Optional[str] = None


class PaymentTimelineItem(BaseModel):
    from_status: Optional[str]
    to_status: str
    reason: Optional[str]
    actor: Optional[str]
    correlation_id: Optional[str]
    at: datetime


class PaymentResponse(BaseModel):
    id: str
    public_id: str
    merchant_id: str
    merchant_reference: str
    amount: int
    currency: str
    status: PaymentStatus
    refunded_amount: int
    needs_review: bool
    provider_reference: Optional[str]
    expires_at: Optional[datetime]
    succeeded_at: Optional[datetime]
    created_at: datetime
    timeline: Optional[List[PaymentTimelineItem]] = None


class CreateRefundRequest(BaseModel):
    amount: int
    currency: str
    reason: Optional[str] = None


class RefundResponse(BaseModel):
    id: str
    public_id: str
    payment_id: str
    amount: int
    currency: str
    status: RefundStatus
    created_by: Optional[str]
    approved_by: Optional[str]
    provider_reference: Optional[str]
    created_at: datetime


class ApproveRefundRequest(BaseModel):
    approved_by: str

