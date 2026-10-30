from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.core.errors import NotFoundError
from payment_lab.db.session import get_db
from sentinelqa.domain.traceability import CoverageGapReport, analyze_coverage_gap
from sentinelqa.db.models import ReleaseDecision, Requirement, RequirementTestLink, TestCase, TestRun
from sentinelqa.services.sentinel_service import SentinelService

router = APIRouter(prefix="/sentinelqa", tags=["SentinelQA Intelligence"])


class CreateRequirementRequest(BaseModel):
    public_id: str
    title: str
    priority: str = "Must"
    severity: str = "High"
    description: str = ""
    acceptance_criteria: Optional[List[str]] = None


class CreateTestCaseRequest(BaseModel):
    public_id: str
    title: str
    level: str = "API"
    priority: str = "P0"
    status: str = "APPROVED"
    origin: str = "HUMAN"
    steps: Optional[List[str]] = None
    expected_result: str = ""
    approved_by: Optional[str] = None


class LinkRequirementTestRequest(BaseModel):
    requirement_public_id: str
    test_case_public_id: str


class RecordTestResultItem(BaseModel):
    test_case_public_id: str
    priority: str = "P0"
    outcome: str  # PASS, FAIL, ERROR, SKIPPED
    error_message: Optional[str] = None
    duration_ms: int = 100


class RecordTestRunRequest(BaseModel):
    commit_sha: str
    environment: str = "test"
    runner_version: str = "pytest-9.0"
    results: List[RecordTestResultItem]


class EvaluateReleaseRequest(BaseModel):
    mutation_score: Optional[float] = None


@router.post("/requirements", status_code=status.HTTP_201_CREATED)
async def create_requirement(
    payload: CreateRequirementRequest,
    db: AsyncSession = Depends(get_db),
):
    req = await SentinelService.create_requirement(
        session=db,
        public_id=payload.public_id,
        title=payload.title,
        priority=payload.priority,
        severity=payload.severity,
        description=payload.description,
        acceptance_criteria=payload.acceptance_criteria,
    )
    return {"id": req.id, "public_id": req.public_id, "title": req.title}


@router.post("/test-cases", status_code=status.HTTP_201_CREATED)
async def create_test_case(
    payload: CreateTestCaseRequest,
    db: AsyncSession = Depends(get_db),
):
    tc = await SentinelService.create_test_case(
        session=db,
        public_id=payload.public_id,
        title=payload.title,
        level=payload.level,
        priority=payload.priority,
        status=payload.status,
        origin=payload.origin,
        steps=payload.steps,
        expected_result=payload.expected_result,
        approved_by=payload.approved_by,
    )
    return {"id": tc.id, "public_id": tc.public_id, "status": tc.status}


@router.post("/links", status_code=status.HTTP_201_CREATED)
async def link_requirement_test(
    payload: LinkRequirementTestRequest,
    db: AsyncSession = Depends(get_db),
):
    link = await SentinelService.link_requirement_and_test(
        session=db,
        requirement_public_id=payload.requirement_public_id,
        test_case_public_id=payload.test_case_public_id,
    )
    return {"id": link.id, "requirement_id": link.requirement_id, "test_case_id": link.test_case_id}


@router.get("/coverage-gap", response_model=CoverageGapReport)
async def get_coverage_gap(
    db: AsyncSession = Depends(get_db),
):
    reqs = (await db.execute(select(Requirement))).scalars().all()
    links = (await db.execute(select(RequirementTestLink))).scalars().all()

    # Get latest result per test case
    runs = (await db.execute(select(TestRun).order_by(TestRun.started_at.desc()).limit(1))).scalars().all()
    latest_results = {}
    if runs:
        latest_results = {r.test_case_id: r.outcome for r in runs[0].results}

    return analyze_coverage_gap(
        requirements=[{"id": req.id, "public_id": req.public_id, "title": req.title, "priority": req.priority, "severity": req.severity} for req in reqs],
        links=[{"requirement_id": l.requirement_id, "test_case_id": l.test_case_id} for l in links],
        latest_results_by_test=latest_results,
    )


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def record_test_run(
    payload: RecordTestRunRequest,
    db: AsyncSession = Depends(get_db),
):
    run = await SentinelService.record_test_run(
        session=db,
        commit_sha=payload.commit_sha,
        environment=payload.environment,
        runner_version=payload.runner_version,
        results_data=[r.model_dump() for r in payload.results],
    )
    return {
        "id": run.id,
        "commit_sha": run.commit_sha,
        "environment": run.environment,
        "total_results": len(run.results),
    }


@router.post("/runs/{run_id}/release-gate")
async def evaluate_release_gate_endpoint(
    run_id: str,
    payload: EvaluateReleaseRequest,
    db: AsyncSession = Depends(get_db),
):
    decision = await SentinelService.evaluate_release(
        session=db,
        run_id=run_id,
        mutation_score=payload.mutation_score,
    )
    return {
        "id": decision.id,
        "run_id": decision.run_id,
        "decision": decision.decision,
        "rule_ids": decision.rule_ids,
        "thresholds": decision.thresholds,
        "input_snapshot": decision.input_snapshot,
    }


@router.get("/runs/{run_id}/release-gate")
async def get_release_decision_endpoint(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ReleaseDecision).where(ReleaseDecision.run_id == run_id)
    decision = (await db.execute(stmt)).scalar_one_or_none()
    if not decision:
        raise NotFoundError("Release decision not found for this test run")
    return {
        "id": decision.id,
        "run_id": decision.run_id,
        "decision": decision.decision,
        "rule_ids": decision.rule_ids,
        "thresholds": decision.thresholds,
        "input_snapshot": decision.input_snapshot,
    }

