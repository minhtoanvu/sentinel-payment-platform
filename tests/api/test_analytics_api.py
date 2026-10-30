import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ts_092_analytics_kpi_calculations_and_sql_sources(client: AsyncClient):
    """
    TS-092 / FR-DASH-003:
    Verify KPI figures and SQL query metrics.
    """
    # 1. Create and confirm a successful payment of 100,000 VND
    c1 = await client.post(
        "/api/v1/payments",
        json={
            "amount": 100000,
            "currency": "VND",
            "payment_method_id": "pm_card_1",
            "merchant_reference": "ord-kpi-1",
        },
        headers={"Idempotency-Key": "idem_kpi_001_succ", "X-Merchant-ID": "m_active_1"},
    )
    assert c1.status_code == 201
    p1_id = c1.json()["id"]

    conf1 = await client.post(
        f"/api/v1/payments/{p1_id}/confirm?scenario=success",
        headers={"X-Merchant-ID": "m_active_1"},
    )
    assert conf1.status_code == 200

    # 2. Refund 30,000 VND on p1
    ref1 = await client.post(
        f"/api/v1/payments/{p1_id}/refunds",
        json={
            "amount": 30000,
            "currency": "VND",
            "reason": "Customer returned goods",
        },
        headers={"Idempotency-Key": "idem_ref_kpi_001", "X-Merchant-ID": "m_active_1"},
    )
    assert ref1.status_code == 201

    # 3. Create a failed payment (decline)
    c2 = await client.post(
        "/api/v1/payments",
        json={
            "amount": 50000,
            "currency": "VND",
            "payment_method_id": "pm_card_1",
            "merchant_reference": "ord-kpi-2",
        },
        headers={"Idempotency-Key": "idem_kpi_002_fail", "X-Merchant-ID": "m_active_1"},
    )
    assert c2.status_code == 201
    p2_id = c2.json()["id"]

    conf2 = await client.post(
        f"/api/v1/payments/{p2_id}/confirm?scenario=decline",
        headers={"X-Merchant-ID": "m_active_1"},
    )
    assert conf2.status_code == 200
    assert conf2.json()["status"] == "FAILED"

    # 4. Query Analytics API
    resp = await client.get("/api/v1/analytics/kpis")
    assert resp.status_code == 200
    data = resp.json()

    pm = data["payment_metrics"]
    assert pm["total_payments"] >= 2
    assert pm["succeeded_payments"] >= 1
    assert "CARD_DECLINED" in pm["failure_breakdown"]
    assert "SELECT count(*)" in pm["sql_source"]

    rm = data["refund_metrics"]
    assert rm["total_refunded_volume"] >= 30000
    assert rm["total_succeeded_volume"] >= 100000
    assert rm["refund_rate_percent"] >= 30.0
    assert "SELECT sum(amount)" in rm["sql_source"]

    resilience = data["resilience_metrics"]
    assert "recovery_rate_percent" in resilience
