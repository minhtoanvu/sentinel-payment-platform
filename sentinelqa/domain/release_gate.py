from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ReleaseGateEvaluation(BaseModel):
    decision: str  # PASS, WARN, BLOCK
    rule_ids: List[str]
    reasons: List[str]
    input_snapshot: Dict[str, Any]
    thresholds: Dict[str, Any]
    ruleset_version: str = "1.0.0"


def evaluate_release_gate(
    test_results: List[Dict[str, Any]],  # [{"test_case_id": ..., "priority": "P0"|"P1"|"P2", "outcome": "PASS"|"FAIL"}]
    coverage_gap_critical_count: int = 0,
    mutation_score: Optional[float] = None,
    min_mutation_threshold: float = 75.0,
    ruleset_version: str = "1.0.0",
) -> ReleaseGateEvaluation:
    """
    FR-GATE-001, FR-GATE-002 / TS-071, TS-072, TS-073:
    Deterministic evaluation of release readiness.
    Produces BLOCK, WARN, or PASS based on strictly deterministic rules.
    """
    rule_ids: List[str] = []
    reasons: List[str] = []
    decision = "PASS"

    # Count failures by priority
    p0_fails = [t for t in test_results if t.get("priority") == "P0" and t.get("outcome") in ("FAIL", "ERROR")]
    p1_fails = [t for t in test_results if t.get("priority") == "P1" and t.get("outcome") in ("FAIL", "ERROR")]

    # Rule RG-01: Critical P0 Test Failure -> BLOCK (TS-071)
    if p0_fails:
        decision = "BLOCK"
        rule_ids.append("RG-FAIL-P0-BLOCK")
        reasons.append(f"Blocked by {len(p0_fails)} failing P0 test cases")

    # Rule RG-02: Critical Requirement Missing Coverage -> BLOCK
    if coverage_gap_critical_count > 0:
        if decision != "BLOCK":
            decision = "BLOCK"
        rule_ids.append("RG-GAP-CRITICAL-BLOCK")
        reasons.append(f"Blocked by {coverage_gap_critical_count} critical requirements lacking passing tests")

    # Rule RG-03: Missing or Low Mutation Score (TS-072)
    # If missing mutation data -> cannot PASS, at least WARN
    if mutation_score is None:
        if decision == "PASS":
            decision = "WARN"
        rule_ids.append("RG-MUTATION-DATA-MISSING")
        reasons.append("Warning: Mutation testing data is missing; cannot issue full PASS")
    elif mutation_score < min_mutation_threshold:
        if decision == "PASS":
            decision = "WARN"
        rule_ids.append("RG-MUTATION-BELOW-THRESHOLD")
        reasons.append(f"Warning: Mutation score ({mutation_score:.1f}%) below threshold ({min_mutation_threshold}%)")

    # Rule RG-04: Non-critical P1 test failures -> WARN
    if p1_fails and decision == "PASS":
        decision = "WARN"
        rule_ids.append("RG-FAIL-P1-WARN")
        reasons.append(f"Warning: {len(p1_fails)} P1 test cases failed")

    if decision == "PASS":
        rule_ids.append("RG-ALL-CHECKS-PASSED")
        reasons.append("All P0 tests passed and quality criteria satisfied")

    input_snapshot = {
        "total_tests": len(test_results),
        "p0_failing": len(p0_fails),
        "p1_failing": len(p1_fails),
        "coverage_gap_critical": coverage_gap_critical_count,
        "mutation_score": mutation_score,
    }

    thresholds = {
        "p0_allowed_fails": 0,
        "min_mutation_score": min_mutation_threshold,
        "critical_gap_allowed": 0,
    }

    return ReleaseGateEvaluation(
        decision=decision,
        rule_ids=rule_ids,
        reasons=reasons,
        input_snapshot=input_snapshot,
        thresholds=thresholds,
        ruleset_version=ruleset_version,
    )

