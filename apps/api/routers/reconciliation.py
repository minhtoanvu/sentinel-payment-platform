from typing import Any, List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.db.models import ReconciliationFinding, ReconciliationRun
from payment_lab.db.session import get_db
from payment_lab.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


class UpdateFindingRequest(BaseModel):
    status: str
    resolved_by: str
    resolution_reason: str


class FindingResponse(BaseModel):
    id: str
    run_id: str
    provider_reference: str
    mismatch_type: str
    severity: str
    status: str
    evidence: Optional[Any] = None
    resolved_by: Optional[str] = None
    resolution_reason: Optional[str] = None


class RunResponse(BaseModel):
    id: str
    provider: str
    business_date: str
    run_no: int
    status: str
    file_checksum: str


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_reconciliation_run(
    provider: str = Form("simulated_provider"),
    business_date: str = Form(...),
    expected_checksum: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    run = await ReconciliationService.process_settlement_file(
        session=db,
        provider=provider,
        business_date=business_date,
        file_content=content,
        expected_checksum=expected_checksum,
    )
    return RunResponse(
        id=run.id,
        provider=run.provider,
        business_date=run.business_date,
        run_no=run.run_no,
        status=run.status,
        file_checksum=run.file_checksum,
    )


@router.get("/runs", response_model=List[RunResponse])
async def list_reconciliation_runs(
    business_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc())
    if business_date:
        stmt = stmt.where(ReconciliationRun.business_date == business_date)
    res = await db.execute(stmt)
    runs = res.scalars().all()
    return [
        RunResponse(
            id=r.id,
            provider=r.provider,
            business_date=r.business_date,
            run_no=r.run_no,
            status=r.status,
            file_checksum=r.file_checksum,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}/findings", response_model=List[FindingResponse])
async def list_findings_for_run(
    run_id: str,
    mismatch_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ReconciliationFinding).where(ReconciliationFinding.run_id == run_id)
    conditions = []
    if mismatch_type:
        conditions.append(ReconciliationFinding.mismatch_type == mismatch_type)
    if status:
        conditions.append(ReconciliationFinding.status == status)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    res = await db.execute(stmt)
    findings = res.scalars().all()
    return [
        FindingResponse(
            id=f.id,
            run_id=f.run_id,
            provider_reference=f.provider_reference,
            mismatch_type=f.mismatch_type,
            severity=f.severity,
            status=f.status,
            evidence=f.evidence,
            resolved_by=f.resolved_by,
            resolution_reason=f.resolution_reason,
        )
        for f in findings
    ]


@router.patch("/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: str,
    payload: UpdateFindingRequest,
    db: AsyncSession = Depends(get_db),
):
    finding = await ReconciliationService.update_finding_status(
        session=db,
        finding_id=finding_id,
        target_status=payload.status,
        resolved_by=payload.resolved_by,
        resolution_reason=payload.resolution_reason,
    )
    return FindingResponse(
        id=finding.id,
        run_id=finding.run_id,
        provider_reference=finding.provider_reference,
        mismatch_type=finding.mismatch_type,
        severity=finding.severity,
        status=finding.status,
        evidence=finding.evidence,
        resolved_by=finding.resolved_by,
        resolution_reason=finding.resolution_reason,
    )

