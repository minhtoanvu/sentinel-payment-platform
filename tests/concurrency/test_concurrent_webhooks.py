import asyncio
import json
import time
import pytest
from httpx import AsyncClient
from payment_lab.simulator.provider_simulator import provider_simulator


@pytest.mark.asyncio
async def test_ts_051_concurrent_webhooks_same_event_id(client: AsyncClient):
    """
    TS-051: Two webhooks with the same event_id sent in parallel.
    Expected: Both return 200, but only one executes side effects; deduplication holds (INV-08).
    """
    now_ts = int(time.time())
    payload = {
        "event_id": "evt_concurrent_ts051",
        "event_type": "payment.succeeded",
        "data": {"payment_id": "non_existent_ref"},
    }
    payload_str = json.dumps(payload)
    sig = provider_simulator.sign_payload(now_ts, payload_str)
    headers = {
        "X-Provider-Timestamp": str(now_ts),
        "X-Provider-Signature": sig,
        "Content-Type": "application/json",
    }

    t1 = client.post("/api/v1/webhooks/provider", content=payload_str, headers=headers)
    t2 = client.post("/api/v1/webhooks/provider", content=payload_str, headers=headers)
    r1, r2 = await asyncio.gather(t1, t2)

    assert r1.status_code == 200
    assert r2.status_code == 200

    dedup_results = [r1.json()["deduplicated"], r2.json()["deduplicated"]]
    # Exactly one request must be primary (deduplicated=False) and the other deduplicated (deduplicated=True)
    assert False in dedup_results
    assert True in dedup_results

