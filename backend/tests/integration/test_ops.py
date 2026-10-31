import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_llm_stats_unauthenticated_rejected(client: AsyncClient) -> None:
    res = await client.get("/api/v1/ops/llm-stats")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_llm_stats(client: AsyncClient) -> None:
    # Authenticated teacher Ms. Rao
    res = await client.get("/api/v1/ops/llm-stats", headers={"X-Demo-User-Id": "2"})
    assert res.status_code == 200
    data = res.json()

    assert "primary_model" in data
    assert "fallback_models" in data
    assert "total_calls" in data
    assert "fallback_rate" in data
    assert "error_rate" in data
    assert "p50_latency_ms" in data
    assert "p95_latency_ms" in data
    assert "models" in data
    assert isinstance(data["models"], list)

    for m in data["models"]:
        assert "model" in m
        assert "circuit_breaker" in m
        assert "state" in m["circuit_breaker"]
        assert "token_budget" in m
        assert "capacity" in m["token_budget"]
