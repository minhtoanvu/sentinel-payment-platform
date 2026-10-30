import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_endpoint_serves_html(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "Payment Lab & SentinelQA Quality Platform" in resp.text

    resp_dash = await client.get("/dashboard")
    assert resp_dash.status_code == 200
    assert "text/html" in resp_dash.headers.get("content-type", "")

