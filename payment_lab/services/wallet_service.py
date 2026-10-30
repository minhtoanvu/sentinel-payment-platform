from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.core.config import settings
from payment_lab.core.errors import InsufficientFundsError, NotFoundError, ValidationError
from payment_lab.domain.invariants import assert_inv_03_wallet_balance_non_negative
from payment_lab.db.models import PaymentMethod, Wallet


class WalletService:
    @staticmethod
    async def get_or_create_wallet(
        session: AsyncSession,
        payment_method_id: str,
        initial_balance: int = 0,
        currency: str = "VND",
    ) -> Wallet:
        """Fetch or create a wallet linked to a payment_method_id."""
        stmt = select(Wallet).where(Wallet.payment_method_id == payment_method_id)
        wallet = (await session.execute(stmt)).scalar_one_or_none()
        if not wallet:
            wallet = Wallet(
                payment_method_id=payment_method_id,
                balance=initial_balance,
                currency=currency,
                updated_at=datetime.now(timezone.utc),
            )
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)
        return wallet

    @staticmethod
    async def deduct_balance(
        session: AsyncSession,
        payment_method_id: str,
        amount: int,
        currency: str = "VND",
    ) -> Wallet:
        """
        Deduct funds from wallet.
        Enforces atomic deduction and INV-03 balance >= 0, unless BUG-016 is active.
        """
        now = datetime.now(timezone.utc)

        if settings.PL_DEFECT_BUG_016:
            # BUG-016: Check-then-act WITHOUT lock (race condition allowed)
            stmt = select(Wallet).where(Wallet.payment_method_id == payment_method_id)
            wallet = (await session.execute(stmt)).scalar_one_or_none()
            if not wallet:
                raise NotFoundError("Wallet not found")

            # Check without lock
            if wallet.balance < amount:
                raise InsufficientFundsError(f"Insufficient funds: balance {wallet.balance} < {amount}")

            # Act: update without lock
            wallet.balance -= amount
            wallet.updated_at = now
            await session.commit()
            await session.refresh(wallet)
            return wallet

        else:
            # Normal: Atomic conditional update (BR-PAY-013 / INV-03)
            update_stmt = (
                update(Wallet)
                .where(
                    and_(
                        Wallet.payment_method_id == payment_method_id,
                        Wallet.balance >= amount,
                    )
                )
                .values(balance=Wallet.balance - amount, updated_at=now)
            )
            res = await session.execute(update_stmt)
            if res.rowcount == 0:
                stmt = select(Wallet).where(Wallet.payment_method_id == payment_method_id)
                wallet = (await session.execute(stmt)).scalar_one_or_none()
                if not wallet:
                    raise NotFoundError("Wallet not found")
                raise InsufficientFundsError(
                    f"Insufficient funds: available {wallet.balance:,} {wallet.currency}, required {amount:,}"
                )

            await session.commit()
            wallet = (await session.execute(select(Wallet).where(Wallet.payment_method_id == payment_method_id))).scalar_one()
            assert_inv_03_wallet_balance_non_negative(wallet.balance)
            return wallet
