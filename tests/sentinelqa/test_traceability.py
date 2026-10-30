import pytest
from sentinelqa.domain.traceability import analyze_coverage_gap


def test_ts_070_coverage_gap_differentiation():
    """
    TS-070 / FR-REQ-003:
    Differentiate 'has test' from 'tested passing'.
    Identify requirements missing all tests or tests never run.
    """
    requirements = [
        {"id": "req-1", "public_id": "FR-PAY-001", "title": "Payment Creation", "priority": "Must", "severity": "Critical"},
        {"id": "req-2", "public_id": "FR-REF-001", "title": "Refund Reservation", "priority": "Must", "severity": "High"},
        {"id": "req-3", "public_id": "FR-WH-001", "title": "Webhook Verification", "priority": "Must", "severity": "High"},
        {"id": "req-4", "public_id": "FR-REC-001", "title": "Reconciliation Engine", "priority": "Should", "severity": "Medium"},
    ]

    links = [
        {"requirement_id": "req-1", "test_case_id": "tc-1"},
        {"requirement_id": "req-2", "test_case_id": "tc-2"},
        {"requirement_id": "req-3", "test_case_id": "tc-3"},
        # req-4 has no test links (missing all tests)
    ]

    latest_results = {
        "tc-1": "PASS",
        "tc-2": "FAIL",
        # tc-3 has not been run yet
    }

    report = analyze_coverage_gap(
        requirements=requirements,
        links=links,
        latest_results_by_test=latest_results,
    )

    assert report.total_requirements == 4
    assert report.covered_passing == 1  # req-1
    assert report.covered_failing == 1  # req-2
    assert report.untested_with_tests == 1  # req-3 (has test tc-3, but never run)
    assert report.missing_all_tests == 1  # req-4 (no test links)
    assert report.coverage_rate == 25.0  # 1/4 = 25%

    gap_statuses = {g.public_id: g.status for g in report.gap_requirements}
    assert "FR-PAY-001" not in gap_statuses  # Passing, not in gap
    assert gap_statuses["FR-REF-001"] == "COVERED_FAILING"
    assert gap_statuses["FR-WH-001"] == "UNTESTED"
    assert gap_statuses["FR-REC-001"] == "NO_TESTS"


def test_coverage_gap_empty_requirements():
    report = analyze_coverage_gap([], [], {})
    assert report.total_requirements == 0
    assert report.coverage_rate == 0.0
    assert len(report.gap_requirements) == 0

