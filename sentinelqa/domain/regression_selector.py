from typing import Dict, List, Optional, Set
from pydantic import BaseModel


class RegressionSelectionResult(BaseModel):
    method: str  # CHANGED_FILE_RULES, RUN_ALL
    selected_test_ids: List[str]
    reasons: Dict[str, str]
    fallback_used: bool
    fallback_reason: Optional[str] = None


class SelectionMetrics(BaseModel):
    recall: float
    precision: float
    time_saved_percent: float


# Mapping of source code paths to impacted test suites
FILE_TO_TEST_MAPPING: Dict[str, List[str]] = {
    "payment_lab/services/payment_service.py": ["TS-001", "TS-012", "TS-013", "TS-018", "TS-031"],
    "payment_lab/services/refund_service.py": ["TS-034", "TS-035", "TS-036", "TS-040", "TS-043"],
    "payment_lab/services/webhook_service.py": ["TS-045", "TS-046", "TS-048", "TS-051"],
    "payment_lab/services/reconciliation_service.py": ["TS-054", "TS-056", "TS-057", "TS-064"],
    "payment_lab/domain/state_machine.py": ["TS-018", "TS-020", "TS-021", "TS-024"],
    "payment_lab/domain/rules.py": ["TS-003", "TS-004", "TS-005", "TS-006", "TS-007"],
    "payment_lab/services/wallet_service.py": ["TS-033"],
}


def select_regression_tests(
    changed_files: Optional[List[str]],
    all_test_ids: List[str],
) -> RegressionSelectionResult:
    """
    FR-IMP-001, FR-IMP-002 / BR-QE-005 / TS-075:
    Select tests affected by git diff changes. Fallback to RUN_ALL when diff is unavailable or ambiguous.
    """
    if changed_files is None or len(changed_files) == 0:
        return RegressionSelectionResult(
            method="RUN_ALL",
            selected_test_ids=all_test_ids,
            reasons={"all": "Fallback triggered: No changed files provided or diff unavailable"},
            fallback_used=True,
            fallback_reason="No diff available",
        )

    selected: Set[str] = set()
    reasons: Dict[str, str] = {}

    for file_path in changed_files:
        norm_path = file_path.replace("\\", "/")
        matched = False
        for pattern, tests in FILE_TO_TEST_MAPPING.items():
            if pattern in norm_path:
                matched = True
                for t in tests:
                    selected.add(t)
                    reasons[t] = f"Impacted by changes in {norm_path}"

        if not matched:
            # If any unmapped core file changed, fallback to RUN_ALL for safety
            return RegressionSelectionResult(
                method="RUN_ALL",
                selected_test_ids=all_test_ids,
                reasons={"all": f"Fallback triggered: Changed file {norm_path} has unknown impact"},
                fallback_used=True,
                fallback_reason=f"Unknown impact for {norm_path}",
            )

    return RegressionSelectionResult(
        method="CHANGED_FILE_RULES",
        selected_test_ids=sorted(list(selected)),
        reasons=reasons,
        fallback_used=False,
    )


def compute_selection_metrics(
    selected_tests: Set[str],
    failing_tests: Set[str],  # Ground truth tests that would catch defects
    all_tests: List[str],
    time_per_test_sec: float = 1.0,
) -> SelectionMetrics:
    """
    FR-IMP-003 / TS-089:
    Calculate recall, precision, and time saved percentage. Handle divide-by-zero cleanly.
    """
    # True Positives: failing tests that were selected
    tp = len(selected_tests.intersection(failing_tests))
    # False Positives: passing tests that were selected
    fp = len(selected_tests - failing_tests)
    # False Negatives: failing tests that were NOT selected
    fn = len(failing_tests - selected_tests)

    # Recall = TP / (TP + FN)
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0

    # Precision = TP / (TP + FP)
    precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0

    # Time Saved
    total_time = len(all_tests) * time_per_test_sec
    selected_time = len(selected_tests) * time_per_test_sec
    time_saved = ((total_time - selected_time) / total_time * 100.0) if total_time > 0 else 0.0

    return SelectionMetrics(
        recall=round(recall, 4),
        precision=round(precision, 4),
        time_saved_percent=round(time_saved, 2),
    )

