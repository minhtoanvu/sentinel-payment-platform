import pytest
from sentinelqa.domain.mutation_engine import MutantItem, calculate_mutation_score


def test_ts_082_valid_mutation_score_calculation():
    mutants = [
        MutantItem(mutant_id="M1", status="KILLED"),
        MutantItem(mutant_id="M2", status="KILLED"),
        MutantItem(mutant_id="M3", status="KILLED"),
        MutantItem(mutant_id="M4", status="SURVIVED"),
        MutantItem(mutant_id="M5", status="EQUIVALENT", justification="Refactored invariant branch is unreachable"),
        MutantItem(mutant_id="M6", status="INVALID"),
    ]

    report = calculate_mutation_score(mutants)

    assert report.total_mutants == 6
    assert report.killed == 3
    assert report.survived == 1
    assert report.equivalent == 1
    assert report.invalid == 1
    # Effective mutants = 6 - 1 (equiv) - 1 (invalid) = 4
    assert report.effective_mutants == 4
    # Score = 3 / 4 * 100 = 75.0%
    assert report.mutation_score == 75.0


def test_ts_082_equivalent_mutant_without_justification_fails():
    mutants = [
        MutantItem(mutant_id="M1", status="EQUIVALENT", justification=""),
    ]
    with pytest.raises(ValueError, match="must provide a justification"):
        calculate_mutation_score(mutants)

    mutants_none = [
        MutantItem(mutant_id="M2", status="EQUIVALENT", justification=None),
    ]
    with pytest.raises(ValueError, match="must provide a justification"):
        calculate_mutation_score(mutants_none)


def test_mutation_score_empty_or_all_invalid():
    report = calculate_mutation_score([])
    assert report.total_mutants == 0
    assert report.mutation_score == 0.0

    all_invalid = [MutantItem(mutant_id="M1", status="INVALID")]
    report_inv = calculate_mutation_score(all_invalid)
    assert report_inv.effective_mutants == 0
    assert report_inv.mutation_score == 0.0

