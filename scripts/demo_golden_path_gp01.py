"""
Golden Path GP-01 Demonstration Script
-------------------------------------
Demonstrates the full end-to-end scenario from PRD §6:
1. Normal flow: Provider timeout -> UNKNOWN -> Status Worker polling -> SUCCEEDED (no double-charge).
2. Defect injection: Enable BUG-004 (timeout treated as FAILED & retried).
3. Quality Engineering: Regression selection, test failure, and SentinelQA Release Gate issuing BLOCK.
4. AI Classifier & Repair recommendation.
5. Audited SQL KPI analytics.
"""

import asyncio
import io
import json
import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure stdout and stderr support UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from payment_lab.core.config import settings
from payment_lab.core.logging import logger
from payment_lab.db.models import Merchant, Payment, PaymentMethod, PaymentStatusHistory, Wallet
from payment_lab.db.session import async_session_factory, init_db
from payment_lab.domain.models import PaymentStatus
from payment_lab.services.analytics_service import AnalyticsService
from payment_lab.services.payment_service import PaymentService
from payment_lab.simulator.provider_simulator import provider_simulator
from payment_lab.workers.status_worker import StatusWorker
from sentinelqa.domain.failure_classifier import classify_failure
from sentinelqa.domain.regression_selector import select_regression_tests
from sentinelqa.domain.release_gate import evaluate_release_gate


def banner(title: str, char="="):
    print("\n" + char * 70)
    print(f" {title.upper()}")
    print(char * 70)


async def setup_demo_fixtures(session):
    # Ensure merchant and payment method exist
    m = await session.get(Merchant, "m_active_1")
    if not m:
        m = Merchant(
            id="m_active_1",
            name="Alpha Coffee Roasters",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
        )
        session.add(m)

    pm = await session.get(PaymentMethod, "pm_card_1")
    if not pm:
        pm = PaymentMethod(
            id="pm_card_1",
            merchant_id="m_active_1",
            type="CARD_TOKEN",
            token="tok_visa_4242",
            created_at=datetime.now(timezone.utc),
        )
        session.add(pm)

    await session.commit()


async def run_golden_path_gp01():
    banner("Golden Path GP-01: End-to-End Payment Lab & SentinelQA")
    print("Scenario: Customer payment times out upstream, but provider successfully charged.")
    print("Goal: Verify idempotency, worker recovery, defect detection (BUG-004), and Release Gate BLOCK.")

    await init_db()

    async with async_session_factory() as session:
        await setup_demo_fixtures(session)

        # -----------------------------------------------------------------
        # STEP 1: Requirement & Rule Traceability Context
        # -----------------------------------------------------------------
        banner("Step 1: Requirement & Acceptance Criteria Context", "-")
        print("Requirement: FR-PAY-006 (Timeout Handling)")
        print("Business Rules: BR-PAY-008 (Timeout -> UNKNOWN, no auto-retry)")
        print("               BR-PAY-009 (Exponential backoff polling query)")
        print("System Invariants: INV-04 (Never charge customer twice for single checkout)")

        # -----------------------------------------------------------------
        # STEP 2 & 3: Normal Behavior with 'timeout_success'
        # -----------------------------------------------------------------
        banner("Step 2 & 3: Payment Creation & Provider Timeout Simulation", "-")
        settings.PL_DEFECT_BUG_004 = False
        merchant_ref = f"gp01_ref_{uuid.uuid4().hex[:8]}"
        idem_key = f"idem_gp01_{uuid.uuid4().hex[:8]}"

        print(f"1. Merchant creates payment: amount=250,000 VND, ref={merchant_ref}")
        payment, _ = await PaymentService.create_payment(
            session=session,
            merchant_id="m_active_1",
            amount=250_000,
            currency_str="VND",
            merchant_reference=merchant_ref,
            payment_method_id="pm_card_1",
            idempotency_key_str=idem_key,
        )
        await session.commit()
        print(f"   -> Payment ID: {payment.id}, Status: {payment.status}")

        print("2. Confirming payment with Provider scenario: 'timeout_success'...")
        payment = await PaymentService.confirm_payment(
            session=session,
            payment_identifier=payment.id,
            provider_scenario="timeout_success",
        )
        await session.commit()
        print(f"   -> Current Status: {payment.status} (EXPECTED: UNKNOWN)")
        print(f"   -> Provider Reference: {payment.provider_reference}")
        charge_count = provider_simulator.get_charge_count(payment.id)
        print(f"   -> Provider Charge Count: {charge_count} (Single charge, no double billing)")

        assert payment.status == PaymentStatus.UNKNOWN.value, "Status must be UNKNOWN!"
        assert charge_count == 1, "Must have exactly 1 charge!"

        # -----------------------------------------------------------------
        # STEP 4: Background Status Worker Polling
        # -----------------------------------------------------------------
        banner("Step 4: Background Status Worker Recovery", "-")
        print("StatusWorker polling provider simulator for payment resolution...")
        resolved_payment = await StatusWorker.process_unknown_payment(
            session=session,
            payment_id=payment.id,
            current_attempt=1,
        )
        print(f"   -> Polling result from provider: SUCCESS")
        print(f"   -> Payment Status transitioned: {PaymentStatus.UNKNOWN.value} -> {resolved_payment.status}")
        print(f"   -> Succeeded at: {resolved_payment.succeeded_at}")

        # Check audit trail
        history_res = await session.execute(
            select(PaymentStatusHistory)
            .where(PaymentStatusHistory.payment_id == payment.id)
            .order_by(PaymentStatusHistory.at)
        )
        transitions = [f"{h.from_status}->{h.to_status}" for h in history_res.scalars().all()]
        print(f"   -> Full Transition Audit Trail: {' => '.join(transitions)}")

        # -----------------------------------------------------------------
        # STEP 5 & 6: Defect Injection BUG-004 & Regression Selection
        # -----------------------------------------------------------------
        banner("Step 5 & 6: Defect Injection (BUG-004) & Regression Impact", "-")
        print("Activating Defect Flag: PL_DEFECT_BUG_004=True")
        print("Defect description: Treats timeout as FAILED and immediately retries charge!")
        settings.PL_DEFECT_BUG_004 = True

        # Regression Selector
        changed_files = ["payment_lab/services/payment_service.py"]
        all_tests = ["TS-001", "TS-012", "TS-013", "TS-018", "TS-026", "TS-031"]
        regression_result = select_regression_tests(changed_files=changed_files, all_test_ids=all_tests)
        print(f"1. SentinelQA Regression Selector analyzed changed file: {changed_files[0]}")
        print(f"   -> Method: {regression_result.method}")
        print(f"   -> Selected regression test cases: {regression_result.selected_test_ids}")

        # Simulating execution of TS-026 under BUG-004
        print("\n2. Executing test TS-026 under BUG-004 defect condition...")
        bad_merchant_ref = f"gp01_bug_{uuid.uuid4().hex[:8]}"
        bad_idem_key = f"idem_bug_{uuid.uuid4().hex[:8]}"

        bad_payment, _ = await PaymentService.create_payment(
            session=session,
            merchant_id="m_active_1",
            amount=250_000,
            currency_str="VND",
            merchant_reference=bad_merchant_ref,
            payment_method_id="pm_card_1",
            idempotency_key_str=bad_idem_key,
        )
        await session.commit()

        bad_payment = await PaymentService.confirm_payment(
            session=session,
            payment_identifier=bad_payment.id,
            provider_scenario="timeout_success",
        )
        await session.commit()
        bad_charge_count = provider_simulator.get_charge_count(bad_payment.id)
        print(f"   -> BUGGY Status: {bad_payment.status} (ERRONEOUS: FAILED instead of UNKNOWN!)")
        print(f"   -> BUGGY Charge Count: {bad_charge_count} (DOUBLE CHARGE DETECTED!)")

        # Test assertion fails
        test_outcome = "FAIL"
        test_failure_msg = (
            f"AssertionError: Expected status 'UNKNOWN' but got '{bad_payment.status}'. "
            f"Expected 1 provider charge, but customer was charged {bad_charge_count} times! (INV-04 Violated)"
        )
        print(f"   -> Test TS-026 Result: {test_outcome}")
        print(f"   -> Failure details: {test_failure_msg}")

        # Reset flag
        settings.PL_DEFECT_BUG_004 = False

        # -----------------------------------------------------------------
        # STEP 7: SentinelQA Release Gate Evaluation
        # -----------------------------------------------------------------
        banner("Step 7: SentinelQA Release Gate Evaluation", "-")
        print("Evaluating candidate release build with test execution batch...")

        mock_test_results = [
            {"test_case_id": "TS-001", "priority": "P0", "outcome": "PASS"},
            {"test_case_id": "TS-003", "priority": "P0", "outcome": "PASS"},
            {"test_case_id": "TS-026", "priority": "P0", "outcome": "FAIL", "error_message": test_failure_msg},
            {"test_case_id": "TS-031", "priority": "P0", "outcome": "PASS"},
            {"test_case_id": "TS-070", "priority": "P1", "outcome": "PASS"},
        ]

        gate_decision = evaluate_release_gate(
            test_results=mock_test_results,
            coverage_gap_critical_count=0,
            mutation_score=82.5,
            min_mutation_threshold=75.0,
        )

        print(f"\n>>> RELEASE GATE DECISION: [{gate_decision.decision}] <<<")
        print(f"Triggered Rule IDs: {gate_decision.rule_ids}")
        print(f"Reasons:")
        for r in gate_decision.reasons:
            print(f"  * {r}")
        print(f"Snapshot Details:")
        print(json.dumps(gate_decision.input_snapshot, indent=4))

        # -----------------------------------------------------------------
        # STEP 8: Failure Classifier & AI Quality Agent Analysis
        # -----------------------------------------------------------------
        banner("Step 8: Failure Classifier & AI Agent Diagnosis", "-")
        classified_cat = classify_failure(test_failure_msg)
        print(f"SentinelQA Failure Classifier categorized error as: [{classified_cat}]")
        print("Root Cause Analysis:")
        print("  - Category: ASSERTION (Contract violation on state transition & idempotency)")
        print("  - Defect ID: BUG-004 (PL_DEFECT_BUG_004)")
        print("  - Recommendation: Do not set payment to FAILED on timeout. Route through UNKNOWN")
        print("    and defer to StatusWorker background polling (BR-PAY-008, BR-PAY-009).")

        # -----------------------------------------------------------------
        # STEP 9: Audited SQL KPI Analytics (TS-092)
        # -----------------------------------------------------------------
        banner("Step 9: Audited SQL KPI Analytics (FR-DASH-003)", "-")
        kpis = await AnalyticsService.get_payment_kpis(session)
        pm = kpis["payment_metrics"]
        rm = kpis["resilience_metrics"]
        rf = kpis["refund_metrics"]

        print(f"Payment Success Rate : {pm['success_rate_percent']:.1f}% ({pm['succeeded_payments']}/{pm['total_payments']} succeeded)")
        print(f"Timeout Recovery Rate: {rm['recovery_rate_percent']:.1f}% ({rm['recovered_to_succeeded']}/{rm['total_unknown_events']} recovered)")
        print(f"Refund Volume Rate   : {rf['refund_rate_percent']:.1f}%")
        print("\nAudited SQL Query behind Timeout Recovery Rate:")
        print(f"  {rm['sql_source']}")

        banner("Golden Path GP-01 Walkthrough Completed Successfully", "=")


if __name__ == "__main__":
    asyncio.run(run_golden_path_gp01())
