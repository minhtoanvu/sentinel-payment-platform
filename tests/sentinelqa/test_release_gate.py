import pytest
from sentinelqa.domain.release_gate import evaluate_release_gate


def test_ts_071_p0_failure_blocks_release():
    """TS-071: Single P0 test failure must trigger BLOCK decision."""
    results = [
        {"test_case_id": "tc-1", "priority": "P0", "outcome": "FAIL"},
        {"test_case_id": "tc-2", "priority": "P0", "outcome": "PASS"},
        {"test_case_id": "tc-3", "priority": "P1", "outcome": "PASS"},
    ]
    eval_res = evaluate_release_gate(test_results=results, mutation_score=85.0)

    assert eval_res.decision == "BLOCK"
    assert "RG-FAIL-P0-BLOCK" in eval_res.rule_ids
    assert eval_res.input_snapshot["p0_failing"] == 1


def test_ts_072_missing_mutation_data_warns():
    """TS-072: All tests pass, but missing mutation score results in WARN."""
    results = [
        {"test_case_id": "tc-1", "priority": "P0", "outcome": "PASS"},
        {"test_case_id": "tc-2", "priority": "P1", "outcome": "PASS"},
    ]
    eval_res = evaluate_release_gate(test_results=results, mutation_score=None)

    assert eval_res.decision == "WARN"
    assert "RG-MUTATION-DATA-MISSING" in eval_res.rule_ids


def test_ts_073_deterministic_evaluation_100_runs():
    """TS-073: 100 repeated evaluations of the identical snapshot produce identical decisions."""
    results = [
        {"test_case_id": "tc-1", "priority": "P0", "outcome": "PASS"},
        {"test_case_id": "tc-2", "priority": "P1", "outcome": "PASS"},
        {"test_case_id": "tc-3", "priority": "P2", "outcome": "FAIL"},
    ]
    first_run = evaluate_release_gate(
        test_results=results,
        coverage_gap_critical_count=0,
        mutation_score=80.0,
    )

    for _ in range(100):
        next_run = evaluate_release_gate(
            test_results=results,
            coverage_gap_critical_count=0,
            mutation_score=80.0,
        )
        assert next_run.decision == first_run.decision
        assert next_run.rule_ids == first_run.rule_ids
        assert next_run.reasons == first_run.reasons
        assert next_run.input_snapshot == first_run.input_snapshot


def test_critical_coverage_gap_blocks_release():
    """Critical requirement coverage gap triggers BLOCK."""
    results = [{"test_case_id": "tc-1", "priority": "P0", "outcome": "PASS"}]
    eval_res = evaluate_release_gate(
        test_results=results,
        coverage_gap_critical_count=2,
        mutation_score=90.0,
    )
    assert eval_res.decision == "BLOCK"
    assert "RG-GAP-CRITICAL-BLOCK" in eval_res.rule_ids


def test_all_checks_passed_decision():
    """All criteria met results in PASS."""
    results = [
        {"test_case_id": "tc-1", "priority": "P0", "outcome": "PASS"},
        {"test_case_id": "tc-2", "priority": "P1", "outcome": "PASS"},
    ]
    eval_res = evaluate_release_gate(
        test_results=results,
        coverage_gap_critical_count=0,
        mutation_score=85.0,
        min_mutation_threshold=75.0,
    )
    assert eval_res.decision == "PASS"
    assert "RG-ALL-CHECKS-PASSED" in eval_res.rule_ids


def test_mutation_score_below_threshold_warns():
    """Mutation score below min_threshold results in WARN."""
    results = [{"test_case_id": "tc-1", "priority": "P0", "outcome": "PASS"}]
    eval_res = evaluate_release_gate(
        test_results=results,
        coverage_gap_critical_count=0,
        mutation_score=60.0,
        min_mutation_threshold=75.0,
    )
    assert eval_res.decision == "WARN"
    assert "RG-MUTATION-BELOW-THRESHOLD" in eval_res.rule_ids


def test_p1_failure_warns():
    """P1 failure with P0 passing results in WARN."""
    results = [
        {"test_case_id": "tc-1", "priority": "P0", "outcome": "PASS"},
        {"test_case_id": "tc-2", "priority": "P1", "outcome": "FAIL"},
    ]
    eval_res = evaluate_release_gate(
        test_results=results,
        coverage_gap_critical_count=0,
        mutation_score=85.0,
    )
    assert eval_res.decision == "WARN"
    assert "RG-FAIL-P1-WARN" in eval_res.rule_ids

