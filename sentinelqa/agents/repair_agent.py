import difflib
from typing import List, Optional
from pydantic import BaseModel, Field
from sentinelqa.agents.llm_adapter import LLMClient


class RepairIteration(BaseModel):
    iteration_number: int
    original_code: str
    repaired_code: str
    diff: str
    summary_of_changes: str


class TestRepairResult(BaseModel):
    test_case_id: str
    status: str  # REPAIRED_PENDING_REVIEW, MAX_ITERATIONS_EXCEEDED, NO_ACTION
    total_iterations: int
    iterations: List[RepairIteration] = Field(default_factory=list)
    final_repaired_code: Optional[str] = None
    requires_human_review: bool = True


class TestRepairAgent:
    """
    FR-AI-005 / BR-AI-001, BR-AI-006 / TS-090:
    Bounded test repair loop. Generates diffs and version history.
    Never overwrites an approved test case directly without human review.
    """

    __test__ = False  # Prevent pytest from collecting this class as a test case

    def __init__(self, llm_client: LLMClient, max_iterations: int = 3):
        self.llm_client = llm_client
        self.max_iterations = max_iterations

    async def propose_repair(
        self,
        test_case_id: str,
        current_test_code: str,
        failure_trace: str,
        error_class: str,
    ) -> TestRepairResult:
        if self.max_iterations <= 0:
            return TestRepairResult(
                test_case_id=test_case_id,
                status="NO_ACTION",
                total_iterations=0,
                requires_human_review=True,
            )

        iterations = []
        code_to_fix = current_test_code

        for i in range(1, self.max_iterations + 1):
            prompt = (
                f"Repair broken test {test_case_id}.\n"
                f"Error Class: {error_class}\n"
                f"Failure Trace: {failure_trace}\n"
                f"Current Code:\n{code_to_fix}\n"
            )

            class LLMRepairOutput(BaseModel):
                repaired_code: str
                summary: str

            resp = await self.llm_client.call_with_retry(
                prompt=prompt,
                response_model=LLMRepairOutput,
                prompt_version="1.0",
            )

            if not resp.is_valid_schema or not resp.data:
                break

            new_code = resp.data.repaired_code
            diff_lines = difflib.unified_diff(
                code_to_fix.splitlines(keepends=True),
                new_code.splitlines(keepends=True),
                fromfile=f"{test_case_id}_v{i}.py",
                tofile=f"{test_case_id}_v{i+1}.py",
            )
            diff_text = "".join(diff_lines)

            iteration = RepairIteration(
                iteration_number=i,
                original_code=code_to_fix,
                repaired_code=new_code,
                diff=diff_text,
                summary_of_changes=resp.data.summary,
            )
            iterations.append(iteration)
            code_to_fix = new_code
            # In a full pipeline, test executor would run against code_to_fix here.
            # Once simulated repaired, loop finishes
            break

        if iterations:
            return TestRepairResult(
                test_case_id=test_case_id,
                status="REPAIRED_PENDING_REVIEW",
                total_iterations=len(iterations),
                iterations=iterations,
                final_repaired_code=iterations[-1].repaired_code,
                requires_human_review=True,  # Mandatory human gate (TS-090)
            )

        return TestRepairResult(
            test_case_id=test_case_id,
            status="MAX_ITERATIONS_EXCEEDED",
            total_iterations=self.max_iterations,
            requires_human_review=True,
        )
