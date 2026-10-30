import re
from typing import Any
from payment_lab.core.config import settings
from payment_lab.core.errors import (
    AmountAboveMaxError,
    AmountBelowMinError,
    IdempotencyKeyRequiredError,
    MerchantInactiveError,
    UnsupportedCurrencyError,
    ValidationError,
)
from payment_lab.domain.models import Currency, MerchantStatus


IDEMPOTENCY_KEY_REGEX = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def validate_idempotency_key(key: str | None) -> str:
    """Validate that the Idempotency-Key header is provided and has 8..64 valid characters."""
    if not key or not isinstance(key, str):
        raise IdempotencyKeyRequiredError("Idempotency-Key header is required")

    trimmed = key.strip()
    if len(trimmed) < 8 or len(trimmed) > 64 or not IDEMPOTENCY_KEY_REGEX.match(trimmed):
        raise IdempotencyKeyRequiredError(
            f"Idempotency-Key must be 8-64 chars matching [A-Za-z0-9_-], got length {len(trimmed)}"
        )
    return trimmed


def validate_currency(currency_str: str) -> Currency:
    """Validate currency is VND or USD."""
    try:
        return Currency(currency_str.upper())
    except (ValueError, AttributeError):
        raise UnsupportedCurrencyError(f"Currency '{currency_str}' is not supported. Supported: VND, USD")


def validate_amount(amount: Any, currency: Currency) -> int:
    """Validate integer amount according to currency boundaries and types."""
    # Check type: must be int, not float, bool, or str
    if type(amount) is not int or isinstance(amount, bool):
        raise ValidationError(
            message="Amount must be an integer (minor unit)",
            details=[{"field": "amount", "issue": "Expected integer, got decimal or non-numeric value"}],
        )

    if amount <= 0:
        raise ValidationError(
            message="Amount must be positive",
            details=[{"field": "amount", "issue": "Amount must be strictly greater than 0"}],
        )

    if currency == Currency.VND:
        if amount < settings.VND_MIN_AMOUNT:
            raise AmountBelowMinError(f"VND amount {amount:,} is below minimum allowed {settings.VND_MIN_AMOUNT:,}")

        # BUG-007 check: defect allows 50,000,001
        max_bound = settings.VND_MAX_AMOUNT + 1 if settings.PL_DEFECT_BUG_007 else settings.VND_MAX_AMOUNT
        if amount > max_bound:
            raise AmountAboveMaxError(f"VND amount {amount:,} exceeds maximum allowed {settings.VND_MAX_AMOUNT:,}")

    elif currency == Currency.USD:
        if amount < settings.USD_MIN_AMOUNT:
            raise AmountBelowMinError(f"USD amount {amount} cents is below minimum allowed {settings.USD_MIN_AMOUNT} cents")

        if amount > settings.USD_MAX_AMOUNT:
            raise AmountAboveMaxError(f"USD amount {amount} cents exceeds maximum allowed {settings.USD_MAX_AMOUNT} cents")

    return amount


def validate_merchant_active(merchant_status: str | MerchantStatus) -> None:
    """Validate merchant account is ACTIVE."""
    status_str = merchant_status.value if isinstance(merchant_status, MerchantStatus) else str(merchant_status)
    if status_str != MerchantStatus.ACTIVE.value:
        raise MerchantInactiveError("Merchant account is inactive")

