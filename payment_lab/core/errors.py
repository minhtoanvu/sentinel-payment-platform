from typing import Any, List, Optional
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: Optional[List[ErrorDetail]] = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class PaymentLabException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[List[dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = [ErrorDetail(**d) for d in (details or [])]


class ValidationError(PaymentLabException):
    def __init__(self, message: str, details: Optional[List[dict[str, Any]]] = None, code: str = "VALIDATION_ERROR"):
        super().__init__(code=code, message=message, status_code=422, details=details)


class AmountBelowMinError(PaymentLabException):
    def __init__(self, message: str = "Amount is below minimum allowed value"):
        super().__init__(code="AMOUNT_BELOW_MIN", message=message, status_code=422, details=[{"field": "amount", "issue": message}])


class AmountAboveMaxError(PaymentLabException):
    def __init__(self, message: str = "Amount exceeds maximum allowed limit"):
        super().__init__(code="AMOUNT_ABOVE_MAX", message=message, status_code=422, details=[{"field": "amount", "issue": message}])


class UnsupportedCurrencyError(PaymentLabException):
    def __init__(self, message: str = "Currency is not supported"):
        super().__init__(code="UNSUPPORTED_CURRENCY", message=message, status_code=422, details=[{"field": "currency", "issue": message}])


class MerchantInactiveError(PaymentLabException):
    def __init__(self, message: str = "Merchant account is inactive"):
        super().__init__(code="MERCHANT_INACTIVE", message=message, status_code=403)


class IdempotencyKeyRequiredError(PaymentLabException):
    def __init__(self, message: str = "Idempotency-Key header is required"):
        super().__init__(code="IDEMPOTENCY_KEY_REQUIRED", message=message, status_code=400)


class IdempotencyKeyReusedError(PaymentLabException):
    def __init__(self, message: str = "Idempotency key reused with different request payload"):
        super().__init__(code="IDEMPOTENCY_KEY_REUSED", message=message, status_code=422)


class RequestInProgressError(PaymentLabException):
    def __init__(self, message: str = "A request with the same idempotency key is currently processing"):
        super().__init__(code="REQUEST_IN_PROGRESS", message=message, status_code=409)


class InvalidStateTransitionError(PaymentLabException):
    def __init__(self, message: str = "Invalid payment state transition"):
        super().__init__(code="INVALID_STATE_TRANSITION", message=message, status_code=409)


class OrderAlreadyPaidError(PaymentLabException):
    def __init__(self, message: str = "Order with this merchant_reference has already been paid"):
        super().__init__(code="ORDER_ALREADY_PAID", message=message, status_code=409)


class PaymentExpiredError(PaymentLabException):
    def __init__(self, message: str = "Payment has expired"):
        super().__init__(code="PAYMENT_EXPIRED", message=message, status_code=410)


class PaymentNotRefundableError(PaymentLabException):
    def __init__(self, message: str = "Payment is not in a refundable state"):
        super().__init__(code="PAYMENT_NOT_REFUNDABLE", message=message, status_code=409)


class RefundExceedsRefundableError(PaymentLabException):
    def __init__(self, message: str = "Refund amount exceeds remaining refundable amount"):
        super().__init__(code="REFUND_EXCEEDS_REFUNDABLE", message=message, status_code=422, details=[{"field": "amount", "issue": message}])


class RefundWindowExpiredError(PaymentLabException):
    def __init__(self, message: str = "Refund window of 180 days has expired"):
        super().__init__(code="REFUND_WINDOW_EXPIRED", message=message, status_code=422)


class RefundLimitReachedError(PaymentLabException):
    def __init__(self, message: str = "Maximum number of refunds reached for this payment"):
        super().__init__(code="REFUND_LIMIT_REACHED", message=message, status_code=422)


class RefundCurrencyMismatchError(PaymentLabException):
    def __init__(self, message: str = "Refund currency does not match payment currency"):
        super().__init__(code="REFUND_CURRENCY_MISMATCH", message=message, status_code=422, details=[{"field": "currency", "issue": message}])


class SelfApprovalNotAllowedError(PaymentLabException):
    def __init__(self, message: str = "Maker cannot approve their own refund request"):
        super().__init__(code="SELF_APPROVAL_NOT_ALLOWED", message=message, status_code=403)


class InvalidSignatureError(PaymentLabException):
    def __init__(self, message: str = "Invalid webhook signature"):
        super().__init__(code="INVALID_SIGNATURE", message=message, status_code=401)


class WebhookTimestampOutOfRangeError(PaymentLabException):
    def __init__(self, message: str = "Webhook timestamp is outside allowed tolerance window"):
        super().__init__(code="WEBHOOK_TIMESTAMP_OUT_OF_RANGE", message=message, status_code=401)


class InsufficientFundsError(PaymentLabException):
    def __init__(self, message: str = "Insufficient wallet funds"):
        super().__init__(code="INSUFFICIENT_FUNDS", message=message, status_code=422)


class FileValidationFailedError(PaymentLabException):
    def __init__(self, message: str, details: Optional[List[dict[str, Any]]] = None):
        super().__init__(code="FILE_VALIDATION_FAILED", message=message, status_code=422, details=details)


class NotFoundError(PaymentLabException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class ForbiddenError(PaymentLabException):
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)

