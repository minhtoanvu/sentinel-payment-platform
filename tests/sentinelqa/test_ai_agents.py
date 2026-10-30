import pytest
from sentinelqa.agents.llm_adapter import LLMClient, MockLLMProvider
from sentinelqa.agents.repair_agent import TestRepairAgent
from sentinelqa.agents.req_to_test_agent import (
    RequirementsToTestsAgent,
    approve_test_case,
    detect_ambiguity,
)


@pytest.mark.asyncio
async def test_ts_077_agent_cannot_self_approve_test():
    """TS-077 / FR-AI-003: AI agent cannot approve test case. Only human can."""
    # Attempt approval with is_agent=True
    with pytest.raises(PermissionError, match="Policy violation: AI agent is not permitted"):
        approve_test_case(
            test_case_status="DRAFT",
            actor_id="agent_sentinel_01",
            actor_role="ai_agent",
            is_agent=True,
        )

    # Attempt approval with human actor
    approved_status = approve_test_case(
        test_case_status="DRAFT",
        actor_id="user_minh_qa",
        actor_role="qa_lead",
        is_agent=False,
    )
    assert approved_status == "APPROVED"


@pytest.mark.asyncio
async def test_ts_078_generate_tests_with_ambiguity_detection():
    """TS-078 / FR-AI-002: Detect vague requirements and flag as ambiguous."""
    # 1. Ambiguous requirement: contains vague buzzwords
    ambiguous_reasons = detect_ambiguity("Hệ thống phải xử lý thanh toán linh hoạt và nhanh chóng nhất v.v.")
    assert len(ambiguous_reasons) > 0

    mock_provider = MockLLMProvider()
    client = LLMClient(provider=mock_provider)
    agent = RequirementsToTestsAgent(client)

    result_ambiguous = await agent.generate_tests(
        requirement_public_id="FR-AMB-001",
        title="Payment Processing",
        description="Thanh toán linh hoạt và nhanh chóng nhất",
    )
    assert result_ambiguous.is_ambiguous is True
    assert len(result_ambiguous.test_cases) == 0

    # 2. Clear, quantified requirement: generates tests linked to requirement ID
    clear_responses = {
        "default": {
            "test_cases": [
                {
                    "title": "Verify payment returns 201 on valid input",
                    "level": "API",
                    "priority": "P0",
                    "technique": "EP",
                    "preconditions": ["Active merchant exists"],
                    "steps": ["POST /payments with 50000 VND"],
                    "expected_result": "Status 201 CREATED",
                    "status": "DRAFT",
                    "origin": "AI",
                }
            ]
        }
    }
    client_clear = LLMClient(provider=MockLLMProvider(default_responses=clear_responses))
    agent_clear = RequirementsToTestsAgent(client_clear)

    result_clear = await agent_clear.generate_tests(
        requirement_public_id="FR-PAY-001",
        title="Create Payment with Valid Parameters",
        description="Amount must be between 1000 and 50000000 VND inclusive",
        acceptance_criteria=["Status code 201 on success", "Payment record created in database"],
    )
    assert result_clear.is_ambiguous is False
    assert len(result_clear.test_cases) == 1
    assert result_clear.test_cases[0].status == "DRAFT"
    assert result_clear.test_cases[0].origin == "AI"


@pytest.mark.asyncio
async def test_ts_080_llm_fault_injection_timeout_and_malformed():
    """TS-080 / FR-AI-001: Gracefully handle timeout or malformed JSON from LLM."""
    # Timeout simulation
    timeout_provider = MockLLMProvider(simulate_timeout=True)
    client_timeout = LLMClient(provider=timeout_provider, max_retries=1, timeout_seconds=0.1)
    agent_timeout = RequirementsToTestsAgent(client_timeout)

    res_timeout = await agent_timeout.generate_tests(
        requirement_public_id="FR-PAY-002",
        title="Check validation boundaries for amount",
        description="Validates positive minor unit integer values",
    )
    assert res_timeout.is_ambiguous is False
    assert len(res_timeout.test_cases) == 0

    # Malformed JSON simulation
    malformed_provider = MockLLMProvider(simulate_malformed_json=True)
    client_malformed = LLMClient(provider=malformed_provider, max_retries=1)
    agent_malformed = RequirementsToTestsAgent(client_malformed)

    res_malformed = await agent_malformed.generate_tests(
        requirement_public_id="FR-PAY-003",
        title="Check validation boundaries for amount",
        description="Validates positive minor unit integer values",
    )
    assert len(res_malformed.test_cases) == 0


@pytest.mark.asyncio
async def test_ts_090_test_repair_loop_diff_and_limits():
    """TS-090 / FR-AI-005: Repair loop produces unified diff and enforces max iterations."""
    repair_responses = {
        "default": {
            "repaired_code": "def test_payment_fixed():\n    assert True\n",
            "summary": "Updated assert condition to match actual API behavior",
        }
    }
    client = LLMClient(provider=MockLLMProvider(default_responses=repair_responses))
    repair_agent = TestRepairAgent(llm_client=client, max_iterations=3)

    result = await repair_agent.propose_repair(
        test_case_id="TS-001",
        current_test_code="def test_payment_fixed():\n    assert False\n",
        failure_trace="AssertionError: assert False",
        error_class="ASSERTION",
    )

    assert result.status == "REPAIRED_PENDING_REVIEW"
    assert result.requires_human_review is True
    assert len(result.iterations) == 1
    diff = result.iterations[0].diff
    assert "-    assert False" in diff
    assert "+    assert True" in diff

