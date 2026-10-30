import pytest
from payment_lab.core.errors import (
    AmountAboveMaxError,
    AmountBelowMinError,
    MerchantInactiveError,
    UnsupportedCurrencyError,
    ValidationError,
)
from payment_lab.domain.models import Currency, MerchantStatus
from payment_lab.domain.rules import (
    validate_amount,
    validate_currency,
    validate_merchant_active,
)


def test_ts_003_amount_zero_and_negative():
    with pytest.raises(ValidationError):
        validate_amount(0, Currency.VND)

    with pytest.raises(ValidationError):
        validate_amount(-1000, Currency.VND)


def test_ts_004_vnd_below_min():
    with pytest.raises(AmountBelowMinError):
        validate_amount(999, Currency.VND)


def test_ts_005_vnd_exact_min():
    assert validate_amount(1_000, Currency.VND) == 1_000


def test_ts_006_vnd_exact_max():
    assert validate_amount(50_000_000, Currency.VND) == 50_000_000


def test_ts_007_vnd_above_max():
    with pytest.raises(AmountAboveMaxError):
        validate_amount(50_000_001, Currency.VND)


def test_ts_008_amount_float_or_string():
    with pytest.raises(ValidationError):
        validate_amount(1000.5, Currency.VND)

    with pytest.raises(ValidationError):
        validate_amount("1000", Currency.VND)


def test_ts_009_usd_boundaries():
    with pytest.raises(AmountBelowMinError):
        validate_amount(49, Currency.USD)

    assert validate_amount(50, Currency.USD) == 50
    assert validate_amount(1_000_000, Currency.USD) == 1_000_000

    with pytest.raises(AmountAboveMaxError):
        validate_amount(1_000_001, Currency.USD)


def test_ts_010_unsupported_currency():
    with pytest.raises(UnsupportedCurrencyError):
        validate_currency("EUR")


def test_ts_011_inactive_merchant():
    with pytest.raises(MerchantInactiveError):
        validate_merchant_active(MerchantStatus.INACTIVE)

