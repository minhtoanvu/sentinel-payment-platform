import re
from typing import List, Optional
from pydantic import BaseModel, Field
from sentinelqa.agents.llm_adapter import LLMClient


class GeneratedTestCase(BaseModel):
    title: str
    level: str = "API"  # UNIT, API, INT, CONC, UI, SEC, AI
    priority: str = "P0"  # P0, P1, P2
    technique: str = "EP"  # EP, BVA, State transition, Concurrency, etc.
    preconditions: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    expected_result: str
    status: str = "DRAFT"  # Must always start in DRAFT
    origin: str = "AI"


class RequirementTestGenerationResult(BaseModel):
    requirement_public_id: str
    is_ambiguous: bool
    ambiguity_reasons: List[str] = Field(default_factory=list)
    test_cases: List[GeneratedTestCase] = Field(default_factory=list)


AMBIGUOUS_KEYWORDS = [
    "tùy biến",
    "linh hoạt",
    "nhanh chóng",
    "tốt nhất",
    "đầy đủ",
    "v.v.",
    "etc.",
    "as appropriate",
    "flexible",
    "fast",
    "user friendly",
]


def detect_ambiguity(text: str) -> List[str]:
    reasons = []
    text_lower = text.lower()
    for kw in AMBIGUOUS_KEYWORDS:
        if kw in text_lower:
            reasons.append(f"Contains ambiguous/unquantified term: '{kw}'")

    if len(text.strip().split()) < 5:
        reasons.append("Description is too brief to define clear acceptance boundaries")

    return reasons


class RequirementsToTestsAgent:
    """
    FR-AI-002 / BR-AI-002 / TS-078:
    Generates test scenarios from requirement specification.
    Guarantees requirement_id attachment, marks ambiguous requirements.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def generate_tests(
        self,
        requirement_public_id: str,
        title: str,
        description: str,
        acceptance_criteria: Optional[List[str]] = None,
    ) -> RequirementTestGenerationResult:
        full_text = f"{title}. {description}. " + " ".join(acceptance_criteria or [])
        ambiguity_reasons = detect_ambiguity(full_text)

        if ambiguity_reasons:
            # Mark requirement as ambiguous, refuse to invent arbitrary rules (BR-AI-002, TS-078)
            return RequirementTestGenerationResult(
                requirement_public_id=requirement_public_id,
                is_ambiguous=True,
                ambiguity_reasons=ambiguity_reasons,
                test_cases=[],
            )

        prompt = (
            f"Generate test cases for requirement: {requirement_public_id}\n"
            f"Title: {title}\n"
            f"Description: {description}\n"
            f"Acceptance Criteria: {acceptance_criteria}\n"
        )

        class LLMTestListOutput(BaseModel):
            test_cases: List[GeneratedTestCase]

        resp = await self.llm_client.call_with_retry(
            prompt=prompt,
            response_model=LLMTestListOutput,
            prompt_version="1.0",
        )

        if not resp.is_valid_schema or not resp.data:
            return RequirementTestGenerationResult(
                requirement_public_id=requirement_public_id,
                is_ambiguous=False,
                ambiguity_reasons=[f"LLM generation failed: {resp.error}"],
                test_cases=[],
            )

        # Enforce that all generated test cases have DRAFT status and origin AI (BR-AI-001)
        tests = []
        for tc in resp.data.test_cases:
            tc_copy = tc.model_copy(update={"status": "DRAFT", "origin": "AI"})
            tests.append(tc_copy)

        return RequirementTestGenerationResult(
            requirement_public_id=requirement_public_id,
            is_ambiguous=False,
            ambiguity_reasons=[],
            test_cases=tests,
        )


def approve_test_case(
    test_case_status: str,
    actor_id: str,
    actor_role: str,
    is_agent: bool,
) -> str:
    """
    FR-AI-003 / BR-AI-001 / TS-077:
    Human review and approval policy.
    AI agents cannot self-approve test cases. Only authorized human roles can approve.
    """
    if is_agent or actor_id.lower().startswith("agent") or actor_role.lower() == "ai_agent":
        raise PermissionError("Policy violation: AI agent is not permitted to approve test cases (BR-AI-001).")

    allowed_roles = {"qa_engineer", "qa_lead", "human_reviewer", "admin"}
    if actor_role.lower() not in allowed_roles:
        raise PermissionError(f"Role '{actor_role}' is not authorized to approve test cases.")

    if test_case_status != "DRAFT":
        raise ValueError(f"Only tests in DRAFT status can be approved. Current status: {test_case_status}")

    return "APPROVED"

