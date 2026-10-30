from typing import Any, Dict, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.db.models import Payment, PaymentStatusHistory, ReconciliationFinding, Refund


class AnalyticsService:
    """
    FR-DASH-003 / BR-REC-007 / TS-092:
    Payment KPI Analytics using independent SQL queries.
    Provides verified figures for dashboard reporting.
    """

    @staticmethod
    async def get_payment_kpis(session: AsyncSession) -> Dict[str, Any]:
        # 1. Total & Succeeded payments
        total_stmt = select(func.count(Payment.id))
        total_payments = (await session.execute(total_stmt)).scalar() or 0

        succeeded_stmt = select(func.count(Payment.id)).where(Payment.status == "SUCCEEDED")
        succeeded_payments = (await session.execute(succeeded_stmt)).scalar() or 0

        success_rate = (succeeded_payments / total_payments * 100.0) if total_payments > 0 else 0.0

        # 2. Failure breakdown by failure reason in status history
        fail_stmt = (
            select(PaymentStatusHistory.reason, func.count(PaymentStatusHistory.id))
            .where(PaymentStatusHistory.to_status == "FAILED")
            .group_by(PaymentStatusHistory.reason)
        )
        fail_rows = (await session.execute(fail_stmt)).all()
        failure_breakdown = {reason or "UNSPECIFIED": count for reason, count in fail_rows}

        # 3. Refund rate: total refunded / total succeeded amount
        total_succeeded_amount_stmt = (
            select(func.sum(Payment.amount))
            .where(Payment.status == "SUCCEEDED")
        )
        total_succeeded_amount = (await session.execute(total_succeeded_amount_stmt)).scalar() or 0

        total_refunded_amount_stmt = (
            select(func.sum(Refund.amount))
            .where(Refund.status == "SUCCEEDED")
        )
        total_refunded_amount = (await session.execute(total_refunded_amount_stmt)).scalar() or 0

        refund_rate = (
            (total_refunded_amount / total_succeeded_amount * 100.0)
            if total_succeeded_amount > 0
            else 0.0
        )

        # 4. Timeout recovery rate: payments with UNKNOWN in status history that became SUCCEEDED
        unknown_audit_stmt = (
            select(PaymentStatusHistory.payment_id)
            .where(PaymentStatusHistory.to_status == "UNKNOWN")
            .distinct()
        )
        unknown_payment_ids = (await session.execute(unknown_audit_stmt)).scalars().all()
        total_unknown_count = len(unknown_payment_ids)

        recovered_count = 0
        if total_unknown_count > 0:
            recovered_stmt = (
                select(func.count(Payment.id))
                .where(
                    Payment.id.in_(unknown_payment_ids),
                    Payment.status == "SUCCEEDED",
                )
            )
            recovered_count = (await session.execute(recovered_stmt)).scalar() or 0

        recovery_rate = (
            (recovered_count / total_unknown_count * 100.0)
            if total_unknown_count > 0
            else 0.0
        )

        # 5. Reconciliation mismatch breakdown
        rec_stmt = (
            select(ReconciliationFinding.mismatch_type, func.count(ReconciliationFinding.id))
            .group_by(ReconciliationFinding.mismatch_type)
        )
        rec_rows = (await session.execute(rec_stmt)).all()
        reconciliation_breakdown = {m_type: count for m_type, count in rec_rows}

        return {
            "payment_metrics": {
                "total_payments": total_payments,
                "succeeded_payments": succeeded_payments,
                "success_rate_percent": round(success_rate, 2),
                "failure_breakdown": failure_breakdown,
                "sql_source": "SELECT count(*) FROM payments WHERE status = 'SUCCEEDED'; SELECT reason, count(*) FROM payment_status_history WHERE to_status = 'FAILED' GROUP BY reason",
            },
            "refund_metrics": {
                "total_succeeded_volume": total_succeeded_amount,
                "total_refunded_volume": total_refunded_amount,
                "refund_rate_percent": round(refund_rate, 2),
                "sql_source": "SELECT sum(amount) FROM refunds WHERE status = 'SUCCEEDED'",
            },
            "resilience_metrics": {
                "total_unknown_events": total_unknown_count,
                "recovered_to_succeeded": recovered_count,
                "recovery_rate_percent": round(recovery_rate, 2),
                "sql_source": "SELECT count(*) FROM payments WHERE id IN (SELECT payment_id FROM payment_status_history WHERE to_status = 'UNKNOWN') AND status = 'SUCCEEDED'",
            },
            "reconciliation_metrics": {
                "mismatch_breakdown": reconciliation_breakdown,
                "total_findings": sum(reconciliation_breakdown.values()),
                "sql_source": "SELECT mismatch_type, count(*) FROM reconciliation_findings GROUP BY mismatch_type",
            },
        }
