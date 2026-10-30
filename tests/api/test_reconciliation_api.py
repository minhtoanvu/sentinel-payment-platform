import io
import pytest
from httpx import AsyncClient
from payment_lab.services.reconciliation_service import ReconciliationService


@pytest.mark.asyncio
async def test_ts_054_perfect_match(client: AsyncClient):
    # Create internal payment
    p_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "ref_rec_054",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_rec_054"},
    )
    p_id = p_resp.json()["id"]
    conf = await client.post(f"/api/v1/payments/{p_id}/confirm?scenario=success")
    provider_ref = conf.json()["provider_reference"]

    # Settlement CSV with exact match
    csv_data = f"provider_reference,amount,currency,status\n{provider_ref},100000,VND,SUCCESS\n"
    checksum = ReconciliationService.compute_checksum(csv_data.encode("utf-8"))

    files = {"file": ("settlement.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    data = {
        "provider": "simulated_provider",
        "business_date": "2026-10-30",
        "expected_checksum": checksum,
    }
    resp = await client.post("/api/v1/reconciliation/runs", data=data, files=files)
    assert resp.status_code == 201
    run_id = resp.json()["id"]

    # Check findings: must be empty
    findings_resp = await client.get(f"/api/v1/reconciliation/runs/{run_id}/findings")
    assert findings_resp.status_code == 200
    assert len(findings_resp.json()) == 0


@pytest.mark.asyncio
async def test_ts_056_missing_in_internal(client: AsyncClient):
    csv_data = "provider_reference,amount,currency,status\next_unknown_ref_123,500000,VND,SUCCESS\n"
    files = {"file": ("settlement.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    data = {"provider": "simulated_provider", "business_date": "2026-10-30"}

    resp = await client.post("/api/v1/reconciliation/runs", data=data, files=files)
    assert resp.status_code == 201
    run_id = resp.json()["id"]

    findings_resp = await client.get(f"/api/v1/reconciliation/runs/{run_id}/findings")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()
    assert len(findings) == 1
    assert findings[0]["mismatch_type"] == "MISSING_IN_INTERNAL"


@pytest.mark.asyncio
async def test_ts_057_amount_mismatch(client: AsyncClient):
    p_resp = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100_000,
            "currency": "VND",
            "merchant_reference": "ref_rec_057",
            "payment_method_id": "pm_card_1",
        },
        headers={"Idempotency-Key": "idem_rec_057"},
    )
    p_id = p_resp.json()["id"]
    conf = await client.post(f"/api/v1/payments/{p_id}/confirm?scenario=success")
    provider_ref = conf.json()["provider_reference"]

    # Settlement file has 90,000 instead of 100,000
    csv_data = f"provider_reference,amount,currency,status\n{provider_ref},90000,VND,SUCCESS\n"
    files = {"file": ("settlement.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    data = {"provider": "simulated_provider", "business_date": "2026-10-30"}

    resp = await client.post("/api/v1/reconciliation/runs", data=data, files=files)
    run_id = resp.json()["id"]

    findings_resp = await client.get(f"/api/v1/reconciliation/runs/{run_id}/findings")
    findings = findings_resp.json()
    assert len(findings) == 1
    assert findings[0]["mismatch_type"] == "AMOUNT_MISMATCH"


@pytest.mark.asyncio
async def test_ts_064_finding_lifecycle(client: AsyncClient):
    csv_data = "provider_reference,amount,currency,status\next_unknown_finding,500000,VND,SUCCESS\n"
    files = {"file": ("settlement.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    data = {"provider": "simulated_provider", "business_date": "2026-10-30"}
    resp = await client.post("/api/v1/reconciliation/runs", data=data, files=files)
    run_id = resp.json()["id"]

    findings = (await client.get(f"/api/v1/reconciliation/runs/{run_id}/findings")).json()
    finding_id = findings[0]["id"]
    assert findings[0]["status"] == "OPEN"

    # Move to INVESTIGATING
    patch1 = await client.patch(
        f"/api/v1/reconciliation/findings/{finding_id}",
        json={
            "status": "INVESTIGATING",
            "resolved_by": "qa_auditor",
            "resolution_reason": "Verifying transaction log with provider support",
        },
    )
    assert patch1.status_code == 200
    assert patch1.json()["status"] == "INVESTIGATING"

    # Move to RESOLVED
    patch2 = await client.patch(
        f"/api/v1/reconciliation/findings/{finding_id}",
        json={
            "status": "RESOLVED",
            "resolved_by": "qa_auditor",
            "resolution_reason": "Confirmed delayed settlement item",
        },
    )
    assert patch2.status_code == 200
    assert patch2.json()["status"] == "RESOLVED"

