from typing import List, Optional
from pydantic import BaseModel


class MutantItem(BaseModel):
    mutant_id: str
    status: str  # KILLED, SURVIVED, EQUIVALENT, INVALID
    justification: Optional[str] = None


class MutationScoreReport(BaseModel):
    total_mutants: int
    killed: int
    survived: int
    equivalent: int
    invalid: int
    effective_mutants: int
    mutation_score: float


def calculate_mutation_score(mutants: List[MutantItem]) -> MutationScoreReport:
    """
    FR-MUT-001 / BR-QE-002 / TS-082:
    Calculate mutation score = killed / (total - equivalent - invalid).
    Validate that equivalent mutants require justification.
    """
    killed = 0
    survived = 0
    equivalent = 0
    invalid = 0

    for m in mutants:
        st = m.status.upper()
        if st == "EQUIVALENT":
            if not m.justification or not m.justification.strip():
                raise ValueError(f"Equivalent mutant '{m.mutant_id}' must provide a justification")
            equivalent += 1
        elif st == "KILLED":
            killed += 1
        elif st == "SURVIVED":
            survived += 1
        elif st == "INVALID":
            invalid += 1

    total = len(mutants)
    effective = total - equivalent - invalid

    score = (killed / effective * 100.0) if effective > 0 else 0.0

    return MutationScoreReport(
        total_mutants=total,
        killed=killed,
        survived=survived,
        equivalent=equivalent,
        invalid=invalid,
        effective_mutants=effective,
        mutation_score=round(score, 2),
    )

