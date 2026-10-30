import pytest
from sentinelqa.domain.regression_selector import (
    compute_selection_metrics,
    select_regression_tests,
)

ALL_TEST_IDS = ["TS-001", "TS-012", "TS-034", "TS-045", "TS-054", "TS-080"]


def test_ts_075_selective_test_execution_on_known_files():
    changed = ["payment_lab/services/refund_service.py"]
    res = select_regression_tests(changed, ALL_TEST_IDS)

    assert res.method == "CHANGED_FILE_RULES"
    assert res.fallback_used is False
    assert "TS-034" in res.selected_test_ids
    assert "TS-035" in res.selected_test_ids
    # Webhook and payment creation tests shouldn't be selected
    assert "TS-045" not in res.selected_test_ids


def test_ts_075_fallback_to_run_all_on_unknown_or_root_file():
    changed = ["payment_lab/core/config.py"]
    res = select_regression_tests(changed, ALL_TEST_IDS)

    assert res.method == "RUN_ALL"
    assert res.fallback_used is True
    assert set(res.selected_test_ids) == set(ALL_TEST_IDS)
    assert "Unknown impact" in res.fallback_reason


def test_ts_075_fallback_to_run_all_on_none_or_empty_diff():
    res_none = select_regression_tests(None, ALL_TEST_IDS)
    assert res_none.method == "RUN_ALL"
    assert res_none.fallback_used is True

    res_empty = select_regression_tests([], ALL_TEST_IDS)
    assert res_empty.method == "RUN_ALL"
    assert res_empty.fallback_used is True


def test_ts_089_compute_selection_metrics():
    all_tests = [f"TS-{i:03d}" for i in range(1, 101)]  # 100 tests
    failing_tests = {"TS-001", "TS-002", "TS-003"}  # 3 ground truth defects
    selected_tests = {"TS-001", "TS-002", "TS-004", "TS-005"}  # 4 selected: 2 TP, 2 FP, 1 FN

    metrics = compute_selection_metrics(
        selected_tests=selected_tests,
        failing_tests=failing_tests,
        all_tests=all_tests,
        time_per_test_sec=2.0,
    )

    # TP = 2, FN = 1 -> Recall = 2 / 3 = 0.6667
    assert metrics.recall == 0.6667
    # TP = 2, FP = 2 -> Precision = 2 / 4 = 0.5
    assert metrics.precision == 0.5
    # Total time = 100 * 2 = 200s, Selected time = 4 * 2 = 8s -> Time saved = 96.0%
    assert metrics.time_saved_percent == 96.0


def test_ts_089_metrics_divide_by_zero_handling():
    metrics = compute_selection_metrics(set(), set(), [])
    assert metrics.recall == 1.0
    assert metrics.precision == 1.0
    assert metrics.time_saved_percent == 0.0

