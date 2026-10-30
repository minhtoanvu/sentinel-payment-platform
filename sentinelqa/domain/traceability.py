from typing import Any, Dict, List, Set
from pydantic import BaseModel


class RequirementCoverageStatus(BaseModel):
    requirement_id: str
    public_id: str
    title: str
    priority: str
    severity: str
    linked_test_count: int
    has_tests: bool
    status: str  # COVERED_PASSING, COVERED_FAILING, UNTESTED, NO_TESTS


class CoverageGapReport(BaseModel):
    total_requirements: int
    covered_passing: int
    covered_failing: int
    untested_with_tests: int
    missing_all_tests: int
    coverage_rate: float
    gap_requirements: List[RequirementCoverageStatus]


def analyze_coverage_gap(
    requirements: List[Dict[str, Any]],
    links: List[Dict[str, str]],  # [{"requirement_id": ..., "test_case_id": ...}]
    latest_results_by_test: Dict[str, str],  # test_case_id -> "PASS"|"FAIL"|"ERROR"
) -> CoverageGapReport:
    """
    FR-REQ-003 / TS-070:
    Differentiate 'has test' from 'tested passing'.
    Identify requirements missing all tests or tests never run.
    """
    req_to_tests: Dict[str, Set[str]] = {}
    for link in links:
        r_id = link["requirement_id"]
        t_id = link["test_case_id"]
        req_to_tests.setdefault(r_id, set()).add(t_id)

    covered_passing = 0
    covered_failing = 0
    untested_with_tests = 0
    missing_all_tests = 0
    gap_list = []

    for req in requirements:
        r_id = req["id"]
        test_ids = req_to_tests.get(r_id, set())

        if not test_ids:
            missing_all_tests += 1
            st = "NO_TESTS"
        else:
            # Check execution outcomes
            outcomes = [latest_results_by_test.get(tid) for tid in test_ids]
            if not any(outcomes):
                # Has tests, but none have been executed!
                untested_with_tests += 1
                st = "UNTESTED"
            elif all(o == "PASS" for o in outcomes if o):
                covered_passing += 1
                st = "COVERED_PASSING"
            else:
                covered_failing += 1
                st = "COVERED_FAILING"

        item = RequirementCoverageStatus(
            requirement_id=r_id,
            public_id=req.get("public_id", ""),
            title=req.get("title", ""),
            priority=req.get("priority", "Must"),
            severity=req.get("severity", "High"),
            linked_test_count=len(test_ids),
            has_tests=len(test_ids) > 0,
            status=st,
        )

        if st in ("NO_TESTS", "UNTESTED", "COVERED_FAILING"):
            gap_list.append(item)

    total = len(requirements)
    rate = (covered_passing / total * 100.0) if total > 0 else 0.0

    return CoverageGapReport(
        total_requirements=total,
        covered_passing=covered_passing,
        covered_failing=covered_failing,
        untested_with_tests=untested_with_tests,
        missing_all_tests=missing_all_tests,
        coverage_rate=round(rate, 2),
        gap_requirements=gap_list,
    )

