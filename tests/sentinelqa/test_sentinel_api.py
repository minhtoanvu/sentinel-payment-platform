import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ts_086_and_087_sentinelqa_api_lifecycle(client: AsyncClient):
    """
    Test SentinelQA complete workflow:
    1. Create requirement
    2. Create test case
    3. Link requirement and test case
    4. Query coverage gap
    5. Record test run
    6. Evaluate Release Gate decision
    7. Query stored Release Gate decision
    """
    # 1. Create requirement
    req_resp = await client.post(
        "/api/v1/sentinelqa/requirements",
        json={
            "public_id": "FR-PAY-TEST",
            "title": "Payment Idempotency Verification",
            "priority": "Must",
            "severity": "Critical",
            "description": "Ensure requests with identical key return original response",
            "acceptance_criteria": ["Return 200 on replay", "Return 409 on payload mismatch"],
        },
    )
    assert req_resp.status_code == 201
    req_data = req_resp.json()
    assert req_data["public_id"] == "FR-PAY-TEST"

    # 2. Create test case
    tc_resp = await client.post(
        "/api/v1/sentinelqa/test-cases",
        json={
            "public_id": "TS-IDEMP-TEST",
            "title": "Test idempotency replay returns 200",
            "level": "API",
            "priority": "P0",
            "status": "APPROVED",
            "origin": "HUMAN",
            "steps": ["Send POST payment", "Replay identical POST"],
            "expected_result": "Both return same payment id",
            "approved_by": "qa_lead",
        },
    )
    assert tc_resp.status_code == 201
    tc_data = tc_resp.json()
    assert tc_data["public_id"] == "TS-IDEMP-TEST"

    # 3. Link requirement and test case
    link_resp = await client.post(
        "/api/v1/sentinelqa/links",
        json={
            "requirement_public_id": "FR-PAY-TEST",
            "test_case_public_id": "TS-IDEMP-TEST",
        },
    )
    assert link_resp.status_code == 201

    # 4. Query coverage gap (before test run: should show UNTESTED)
    gap_resp = await client.get("/api/v1/sentinelqa/coverage-gap")
    assert gap_resp.status_code == 200
    gap_data = gap_resp.json()
    assert gap_data["total_requirements"] >= 1
    assert gap_data["untested_with_tests"] >= 1

    # 5. Record test run with PASS result
    run_resp = await client.post(
        "/api/v1/sentinelqa/runs",
        json={
            "commit_sha": "a1b2c3d4e5f67890",
            "environment": "ci",
            "runner_version": "pytest-9.0.3",
            "results": [
                {
                    "test_case_public_id": "TS-IDEMP-TEST",
                    "priority": "P0",
                    "outcome": "PASS",
                    "duration_ms": 120,
                }
            ],
        },
    )
    assert run_resp.status_code == 201
    run_data = run_resp.json()
    run_id = run_data["id"]
    assert run_data["total_results"] == 1

    # 6. Evaluate Release Gate: with mutation score >= 75% -> PASS
    gate_eval_resp = await client.post(
        f"/api/v1/sentinelqa/runs/{run_id}/release-gate",
        json={"mutation_score": 82.5},
    )
    assert gate_eval_resp.status_code == 200
    gate_data = gate_eval_resp.json()
    assert gate_data["decision"] == "PASS"
    assert "RG-ALL-CHECKS-PASSED" in gate_data["rule_ids"]

    # 7. Query stored Release Gate decision
    get_gate_resp = await client.get(f"/api/v1/sentinelqa/runs/{run_id}/release-gate")
    assert get_gate_resp.status_code == 200
    stored_data = get_gate_resp.json()
    assert stored_data["decision"] == "PASS"
    assert stored_data["rule_ids"] == gate_data["rule_ids"]


@pytest.mark.asyncio
async def test_get_nonexistent_release_decision_returns_404(client: AsyncClient):
    resp = await client.get("/api/v1/sentinelqa/runs/non-existent-id/release-gate")
    assert resp.status_code == 404

