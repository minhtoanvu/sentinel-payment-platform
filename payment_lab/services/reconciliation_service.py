import csv
import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from zoneinfo import ZoneInfo
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.core.config import settings
from payment_lab.core.errors import (
    FileValidationFailedError,
    NotFoundError,
    ValidationError,
)
from payment_lab.domain.invariants import assert_inv_07_reconciliation_conservation
from payment_lab.domain.models import FindingStatus, MismatchType
from payment_lab.db.models import (
    Payment,
    ReconciliationFinding,
    ReconciliationItem,
    ReconciliationQuarantine,
    ReconciliationRun,
)


class ReconciliationService:
    @staticmethod
    def compute_checksum(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def get_business_date(dt: datetime) -> str:
        """Calculate business date based on configured timezone (Asia/Ho_Chi_Minh) unless BUG-010."""
        if settings.PL_DEFECT_BUG_010:
            # BUG-010: Uses UTC instead of +07
            utc_dt = dt.astimezone(timezone.utc)
            return utc_dt.strftime("%Y-%m-%d")
        else:
            tz = ZoneInfo(settings.BUSINESS_TIMEZONE)
            local_dt = dt.astimezone(tz)
            return local_dt.strftime("%Y-%m-%d")

    @staticmethod
    async def process_settlement_file(
        session: AsyncSession,
        provider: str,
        business_date: str,
        file_content: bytes,
        expected_checksum: Optional[str] = None,
    ) -> ReconciliationRun:
        """
        Parse settlement CSV, validate structure, perform reconciliation, and record findings.
        """
        now = datetime.now(timezone.utc)

        # 1. Validate Checksum
        computed_checksum = ReconciliationService.compute_checksum(file_content)
        if expected_checksum and computed_checksum != expected_checksum:
            raise FileValidationFailedError(
                f"File checksum mismatch. Expected {expected_checksum}, got {computed_checksum}"
            )

        # 2. Check Previous Runs & Supersede (BR-REC-005)
        run_stmt = select(ReconciliationRun).where(
            and_(
                ReconciliationRun.provider == provider,
                ReconciliationRun.business_date == business_date,
            )
        )
        existing_runs = (await session.execute(run_stmt)).scalars().all()
        run_no = len(existing_runs) + 1

        if not settings.PL_DEFECT_BUG_013:
            # Supersede old active runs
            for old_run in existing_runs:
                if old_run.status == "ACTIVE":
                    old_run.status = "SUPERSEDED"

        run_id = str(uuid.uuid4())
        run = ReconciliationRun(
            id=run_id,
            provider=provider,
            business_date=business_date,
            run_no=run_no,
            status="ACTIVE",
            file_checksum=computed_checksum,
            created_at=now,
        )
        session.add(run)
        await session.flush()

        # 3. Parse CSV lines
        text_stream = io.StringIO(file_content.decode("utf-8-sig", errors="replace"))
        reader = csv.DictReader(text_stream)

        required_columns = {"provider_reference", "amount", "currency", "status"}
        if not reader.fieldnames or not required_columns.issubset(set(reader.fieldnames)):
            raise FileValidationFailedError(
                f"Missing required CSV columns. Required: {required_columns}, found: {reader.fieldnames}"
            )

        provider_records: dict[str, dict[str, Any]] = {}
        seen_refs: set[str] = set()

        line_no = 1
        for row in reader:
            line_no += 1
            pref = (row.get("provider_reference") or "").strip()
            amount_str = (row.get("amount") or "").strip()
            curr = (row.get("currency") or "").strip().upper()
            status_str = (row.get("status") or "").strip().upper()

            # Quarantine bad rows
            if not pref or not amount_str:
                session.add(
                    ReconciliationQuarantine(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        line_no=line_no,
                        reason="Missing provider_reference or amount",
                        raw_line=str(row),
                        created_at=now,
                    )
                )
                continue

            try:
                amt = int(amount_str)
            except ValueError:
                session.add(
                    ReconciliationQuarantine(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        line_no=line_no,
                        reason=f"Invalid non-integer amount '{amount_str}'",
                        raw_line=str(row),
                        created_at=now,
                    )
                )
                continue

            # Check duplicate in provider file
            if pref in seen_refs:
                session.add(
                    ReconciliationFinding(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        provider_reference=pref,
                        mismatch_type=MismatchType.DUPLICATE_IN_PROVIDER.value,
                        severity="MEDIUM",
                        status=FindingStatus.OPEN.value,
                        evidence={"line_no": line_no, "row": row},
                        created_at=now,
                    )
                )
                continue

            seen_refs.add(pref)
            provider_records[pref] = {
                "amount": amt,
                "currency": curr,
                "status": status_str,
                "line_no": line_no,
                "row": row,
            }

        # 4. Fetch internal payments for this date / provider references
        all_refs = list(provider_records.keys())
        p_stmt = select(Payment).where(Payment.provider_reference.isnot(None))
        p_res = await session.execute(p_stmt)
        internal_payments = {p.provider_reference: p for p in p_res.scalars().all() if p.provider_reference}

        matched_refs = set()
        mismatched_refs = set()

        # Compare provider records against internal records
        for pref, p_data in provider_records.items():
            internal_payment = internal_payments.get(pref)

            if not internal_payment:
                # Missing in internal
                mismatched_refs.add(pref)
                session.add(
                    ReconciliationFinding(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        provider_reference=pref,
                        mismatch_type=MismatchType.MISSING_IN_INTERNAL.value,
                        severity="HIGH",
                        status=FindingStatus.OPEN.value,
                        evidence={"provider_record": p_data},
                        created_at=now,
                    )
                )
                session.add(
                    ReconciliationItem(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        provider_reference=pref,
                        match_result="MISMATCHED",
                    )
                )
                continue

            # Compare currency
            if p_data["currency"] != internal_payment.currency:
                mismatched_refs.add(pref)
                session.add(
                    ReconciliationFinding(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        provider_reference=pref,
                        mismatch_type=MismatchType.CURRENCY_MISMATCH.value,
                        severity="HIGH",
                        status=FindingStatus.OPEN.value,
                        evidence={"provider": p_data["currency"], "internal": internal_payment.currency},
                        created_at=now,
                    )
                )

            # Compare amount: BUG-009 converts USD to float
            is_amount_mismatch = False
            if settings.PL_DEFECT_BUG_009 and p_data["currency"] == "USD":
                # BUG-009: converts USD to float, creating subtle floating-point precision error
                f_prov = float(p_data["amount"]) / 100.0
                f_int = float(internal_payment.amount) / 100.0 + 0.0000000001
                if abs(f_prov - f_int) > 1e-12:
                    is_amount_mismatch = True
            else:
                if p_data["amount"] != internal_payment.amount:
                    is_amount_mismatch = True

            if is_amount_mismatch:
                mismatched_refs.add(pref)
                session.add(
                    ReconciliationFinding(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        provider_reference=pref,
                        mismatch_type=MismatchType.AMOUNT_MISMATCH.value,
                        severity="HIGH",
                        status=FindingStatus.OPEN.value,
                        evidence={"provider_amount": p_data["amount"], "internal_amount": internal_payment.amount},
                        created_at=now,
                    )
                )

            # Compare status
            prov_success = p_data["status"] in ("SUCCESS", "SETTLED", "SUCCEEDED")
            int_success = internal_payment.status == "SUCCEEDED"
            if prov_success != int_success:
                mismatched_refs.add(pref)
                session.add(
                    ReconciliationFinding(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        provider_reference=pref,
                        mismatch_type=MismatchType.STATUS_MISMATCH.value,
                        severity="HIGH",
                        status=FindingStatus.OPEN.value,
                        evidence={"provider_status": p_data["status"], "internal_status": internal_payment.status},
                        created_at=now,
                    )
                )

            if pref not in mismatched_refs:
                matched_refs.add(pref)
                session.add(
                    ReconciliationItem(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        provider_reference=pref,
                        match_result="MATCHED",
                    )
                )
            else:
                session.add(
                    ReconciliationItem(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        provider_reference=pref,
                        match_result="MISMATCHED",
                    )
                )

        # 5. Check Internal payments missing in provider file (for payments with same business_date)
        for pref, p in internal_payments.items():
            if pref not in provider_records:
                # If payment happened on this business_date
                p_bdate = ReconciliationService.get_business_date(p.created_at)
                if p_bdate == business_date:
                    mismatched_refs.add(pref)
                    session.add(
                        ReconciliationFinding(
                            id=str(uuid.uuid4()),
                            run_id=run_id,
                            provider_reference=pref,
                            mismatch_type=MismatchType.MISSING_IN_PROVIDER.value,
                            severity="HIGH",
                            status=FindingStatus.OPEN.value,
                            evidence={"payment_id": p.id, "amount": p.amount, "status": p.status},
                            created_at=now,
                        )
                    )
                    session.add(
                        ReconciliationItem(
                            id=str(uuid.uuid4()),
                            run_id=run_id,
                            provider_reference=pref,
                            match_result="MISMATCHED",
                        )
                    )

        # 6. Verify Invariant INV-07 (Conservation Law)
        total_unique = len(matched_refs) + len(mismatched_refs)
        assert_inv_07_reconciliation_conservation(
            total_references=total_unique,
            matched_count=len(matched_refs),
            mismatched_unique_refs=len(mismatched_refs),
        )

        await session.commit()
        await session.refresh(run)
        return run

    @staticmethod
    async def update_finding_status(
        session: AsyncSession,
        finding_id: str,
        target_status: str,
        resolved_by: str,
        resolution_reason: str,
    ) -> ReconciliationFinding:
        """
        Transition finding lifecycle: OPEN -> INVESTIGATING -> RESOLVED / WRITTEN_OFF (BR-REC-006).
        Requires resolved_by and resolution_reason.
        """
        if not resolved_by or not resolution_reason:
            raise ValidationError("resolved_by and resolution_reason are required to update finding")

        stmt = select(ReconciliationFinding).where(ReconciliationFinding.id == finding_id)
        result = await session.execute(stmt)
        finding = result.scalar_one_or_none()
        if not finding:
            raise NotFoundError("Reconciliation finding not found")

        valid_statuses = {
            FindingStatus.OPEN.value,
            FindingStatus.INVESTIGATING.value,
            FindingStatus.RESOLVED.value,
            FindingStatus.WRITTEN_OFF.value,
        }
        if target_status not in valid_statuses:
            raise ValidationError(f"Invalid target status '{target_status}'")

        finding.status = target_status
        finding.resolved_by = resolved_by
        finding.resolution_reason = resolution_reason

        await session.commit()
        await session.refresh(finding)
        return finding

