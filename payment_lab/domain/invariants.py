"""System Invariants for Payment Lab (INV-01 to INV-08)."""
from typing import List
from payment_lab.domain.models import PaymentStatus, RefundStatus


def assert_inv_01_single_succeeded(succeeded_count: int, merchant_ref: str) -> None:
    """INV-01: At most one payment with the same merchant_reference can be SUCCEEDED."""
    assert succeeded_count <= 1, (
        f"INV-01 violated: Found {succeeded_count} SUCCEEDED payments for merchant_reference '{merchant_ref}'"
    )


def assert_inv_02_refund_never_exceeds_amount(total_succeeded_refunds: int, payment_amount: int) -> None:
    """INV-02: Total SUCCEEDED refunds must never exceed payment.amount."""
    assert total_succeeded_refunds <= payment_amount, (
        f"INV-02 violated: Total refunded ({total_succeeded_refunds}) > payment amount ({payment_amount})"
    )


def assert_inv_03_wallet_balance_non_negative(balance: int) -> None:
    """INV-03: Wallet balance must be >= 0 at all times."""
    assert balance >= 0, f"INV-03 violated: Wallet balance is negative ({balance})"


def assert_inv_05_terminal_status_immutable(original_status: PaymentStatus, target_status: PaymentStatus) -> None:
    """INV-05: A terminal status must never be updated to a different status."""
    if original_status.is_terminal and target_status != original_status:
        raise AssertionError(
            f"INV-05 violated: Attempted transition from terminal '{original_status.value}' to '{target_status.value}'"
        )


def assert_inv_07_reconciliation_conservation(
    total_references: int,
    matched_count: int,
    mismatched_unique_refs: int,
) -> None:
    """INV-07: total_unique_references = matched + references_with_mismatch."""
    assert total_references == matched_count + mismatched_unique_refs, (
        f"INV-07 violated: {total_references} != {matched_count} + {mismatched_unique_refs}"
    )

