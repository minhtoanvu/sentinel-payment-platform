import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.core.errors import NotFoundError, ValidationError
from sentinelqa.domain.failure_classifier import classify_failure
from sentinelqa.domain.release_gate import evaluate_release_gate
from sentinelqa.domain.traceability import analyze_coverage_gap
from sentinelqa.db.models import (
    ReleaseDecision,
    Requirement,
    RequirementTestLink,
    RequirementVersion,
    TestCase,
    TestCaseVersion,
    TestResult,
    TestRun,
)


class SentinelService:
    @staticmethod
    async def create_requirement(
        session: AsyncSession,
        public_id: str,
        title: str,
        priority: str = "Must",
        severity: str = "High",
        description: str = "",
        acceptance_criteria: Optional[List[str]] = None,
    ) -> Requirement:
        """
        FR-REQ-001 / TS-086:
        Create or update requirement. Updating creates a new version, preserving history.
        """
        now = datetime.now(timezone.utc)
        stmt = select(Requirement).where(Requirement.public_id == public_id)
        req = (await session.execute(stmt)).scalar_one_or_none()

        if not req:
            req_id = str(uuid.uuid4())
            req = Requirement(
                id=req_id,
                public_id=public_id,
                title=title,
                priority=priority,
                severity=severity,
                created_at=now,
            )
            session.add(req)
            session.add(
                RequirementVersion(
                    id=str(uuid.uuid4()),
                    requirement_id=req_id,
                    version=1,
                    description=description,
                    acceptance_criteria=acceptance_criteria or [],
                    created_at=now,
                )
            )
        else:
            # Update creates a new version
            latest_v = max([v.version for v in req.versions], default=0)
            req.title = title
            req.priority = priority
            req.severity = severity
            session.add(
                RequirementVersion(
                    id=str(uuid.uuid4()),
                    requirement_id=req.id,
                    version=latest_v + 1,
                    description=description,
                    acceptance_criteria=acceptance_criteria or [],
                    created_at=now,
                )
            )

        await session.commit()
        await session.refresh(req)
        return req

    @staticmethod
    async def create_test_case(
        session: AsyncSession,
        public_id: str,
        title: str,
        level: str = "API",
        priority: str = "P0",
        status: str = "APPROVED",
        origin: str = "HUMAN",
        steps: Optional[List[str]] = None,
        expected_result: str = "",
        approved_by: Optional[str] = None,
    ) -> TestCase:
        """
        FR-TC-001 / TS-087:
        Create or update test case. Validates lifecycle transitions (DRAFT -> APPROVED -> DEPRECATED).
        """
        now = datetime.now(timezone.utc)
        stmt = select(TestCase).where(TestCase.public_id == public_id)
        tc = (await session.execute(stmt)).scalar_one_or_none()

        valid_transitions = {
            "DRAFT": {"APPROVED", "DEPRECATED"},
            "APPROVED": {"DEPRECATED"},
            "DEPRECATED": set(),
        }

        if not tc:
            tc_id = str(uuid.uuid4())
            tc = TestCase(
                id=tc_id,
                public_id=public_id,
                title=title,
                level=level,
                priority=priority,
                status=status,
                origin=origin,
                created_at=now,
            )
            session.add(tc)
            session.add(
                TestCaseVersion(
                    id=str(uuid.uuid4()),
                    test_case_id=tc_id,
                    version=1,
                    steps=steps or [],
                    expected_result=expected_result,
                    approved_by=approved_by,
                    created_at=now,
                )
            )
        else:
            # Check lifecycle transition validity
            if status != tc.status and status not in valid_transitions.get(tc.status, set()):
                raise ValidationError(f"Invalid test case transition from {tc.status} to {status}")

            latest_v = max([v.version for v in tc.versions], default=0)
            tc.title = title
            tc.level = level
            tc.priority = priority
            tc.status = status
            session.add(
                TestCaseVersion(
                    id=str(uuid.uuid4()),
                    test_case_id=tc.id,
                    version=latest_v + 1,
                    steps=steps or [],
                    expected_result=expected_result,
                    approved_by=approved_by,
                    created_at=now,
                )
            )

        await session.commit()
        await session.refresh(tc)
        return tc

    @staticmethod
    async def link_requirement_and_test(
        session: AsyncSession,
        requirement_public_id: str,
        test_case_public_id: str,
    ) -> RequirementTestLink:
        """Link a requirement and test case."""
        r_stmt = select(Requirement).where(Requirement.public_id == requirement_public_id)
        req = (await session.execute(r_stmt)).scalar_one_or_none()
        if not req:
            raise NotFoundError(f"Requirement '{requirement_public_id}' not found")

        t_stmt = select(TestCase).where(TestCase.public_id == test_case_public_id)
        tc = (await session.execute(t_stmt)).scalar_one_or_none()
        if not tc:
            raise NotFoundError(f"Test case '{test_case_public_id}' not found")

        # Check existing link
        link_stmt = select(RequirementTestLink).where(
            and_(RequirementTestLink.requirement_id == req.id, RequirementTestLink.test_case_id == tc.id)
        )
        existing = (await session.execute(link_stmt)).scalar_one_or_none()
        if existing:
            return existing

        link = RequirementTestLink(
            id=str(uuid.uuid4()),
            requirement_id=req.id,
            test_case_id=tc.id,
        )
        session.add(link)
        await session.commit()
        return link

    @staticmethod
    async def record_test_run(
        session: AsyncSession,
        commit_sha: str,
        environment: str = "test",
        runner_version: str = "pytest-9.0",
        results_data: Optional[List[Dict[str, Any]]] = None,
    ) -> TestRun:
        """
        FR-RUN-001 / TS-074:
        Record test run with commit_sha, environment, runner_version, duration and failure classification.
        """
        now = datetime.now(timezone.utc)
        run_id = str(uuid.uuid4())
        run = TestRun(
            id=run_id,
            commit_sha=commit_sha,
            environment=environment,
            runner_version=runner_version,
            started_at=now,
            finished_at=now,
        )
        session.add(run)

        for item in (results_data or []):
            tc_pub_id = item["test_case_public_id"]
            tc = (await session.execute(select(TestCase).where(TestCase.public_id == tc_pub_id))).scalar_one_or_none()
            if not tc:
                # Auto-create placeholder test case if not registered
                tc = TestCase(
                    id=str(uuid.uuid4()),
                    public_id=tc_pub_id,
                    title=f"Test {tc_pub_id}",
                    priority=item.get("priority", "P0"),
                    created_at=now,
                )
                session.add(tc)
                await session.flush()

            outcome = item.get("outcome", "PASS")
            error_msg = item.get("error_message")
            f_class = classify_failure(error_msg) if outcome in ("FAIL", "ERROR") else "NONE"

            res = TestResult(
                id=str(uuid.uuid4()),
                run_id=run_id,
                test_case_id=tc.id,
                outcome=outcome,
                failure_class=f_class,
                duration_ms=item.get("duration_ms", 100),
                error_message=error_msg,
            )
            session.add(res)

        await session.commit()
        await session.refresh(run)
        return run

    @staticmethod
    async def evaluate_release(
        session: AsyncSession,
        run_id: str,
        mutation_score: Optional[float] = None,
    ) -> ReleaseDecision:
        """
        FR-GATE-001, FR-GATE-002:
        Evaluate Release Gate and store immutable decision record.
        """
        stmt = select(TestRun).where(TestRun.id == run_id)
        run = (await session.execute(stmt)).scalar_one_or_none()
        if not run:
            raise NotFoundError("Test run not found")

        # Map results to input format
        test_inputs = []
        for r in run.results:
            test_inputs.append({
                "test_case_id": r.test_case.public_id,
                "priority": r.test_case.priority,
                "outcome": r.outcome,
            })

        # Check coverage gap for critical requirements
        reqs = (await session.execute(select(Requirement))).scalars().all()
        links = (await session.execute(select(RequirementTestLink))).scalars().all()

        latest_results = {r.test_case_id: r.outcome for r in run.results}
        gap_report = analyze_coverage_gap(
            requirements=[{"id": req.id, "public_id": req.public_id, "title": req.title, "priority": req.priority, "severity": req.severity} for req in reqs],
            links=[{"requirement_id": l.requirement_id, "test_case_id": l.test_case_id} for l in links],
            latest_results_by_test=latest_results,
        )

        critical_gaps = [g for g in gap_report.gap_requirements if g.severity == "Critical"]

        eval_result = evaluate_release_gate(
            test_results=test_inputs,
            coverage_gap_critical_count=len(critical_gaps),
            mutation_score=mutation_score,
        )

        decision = ReleaseDecision(
            id=str(uuid.uuid4()),
            run_id=run_id,
            decision=eval_result.decision,
            rule_ids=eval_result.rule_ids,
            input_snapshot=eval_result.input_snapshot,
            thresholds=eval_result.thresholds,
            ruleset_version=eval_result.ruleset_version,
            created_at=datetime.now(timezone.utc),
        )
        session.add(decision)
        await session.commit()
        await session.refresh(decision)
        return decision

