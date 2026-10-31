from fastapi import APIRouter

from app.ai.llm.recorder import recorder
from app.ai.llm.router import router
from app.schemas.ops import (
    LLMStatsResponse,
    ModelBreakerStatus,
    ModelStatusOut,
    ModelTokenBudgetStatus,
    RecentCallOut,
)

router_api = APIRouter(prefix="/ops", tags=["Operations & Observability"])


@router_api.get("/llm-stats", response_model=LLMStatsResponse)
async def get_llm_stats() -> LLMStatsResponse:
    """Returns telemetry on language models: latency percentiles, error rates, circuit breakers, and budgets."""
    router_status = router.get_status()
    stats = recorder.get_recent_stats()

    models_out: list[ModelStatusOut] = []
    models_stats_map = stats.get("models", {})

    for m in router_status.get("models", []):
        m_name = m["model"]
        m_stat = models_stats_map.get(m_name, {})
        m_breaker = m["circuit_breaker"]
        m_budget = m["token_budget"]

        models_out.append(
            ModelStatusOut(
                model=m_name,
                is_primary=m["is_primary"],
                circuit_breaker=ModelBreakerStatus(
                    model=m_breaker["model"],
                    state=m_breaker["state"],
                    failure_count=m_breaker["failure_count"],
                    seconds_until_reset=m_breaker["seconds_until_reset"],
                ),
                token_budget=ModelTokenBudgetStatus(
                    capacity=m_budget["capacity"],
                    available=m_budget["available"],
                    pct_remaining=m_budget["pct_remaining"],
                ),
                calls=m_stat.get("calls", 0),
                errors=m_stat.get("errors", 0),
                avg_latency_ms=m_stat.get("avg_latency_ms", 0),
                tokens_consumed=m_stat.get("prompt_tokens", 0) + m_stat.get("completion_tokens", 0),
            )
        )

    recent_calls = [
        RecentCallOut(
            purpose=c["purpose"],
            model=c["model"],
            latency_ms=c["latency_ms"],
            status=c["status"],
            fallback_used=c["fallback_used"],
            tokens=c["tokens"],
            created_at=c["created_at"],
        )
        for c in stats.get("recent_calls", [])
    ]

    return LLMStatsResponse(
        primary_model=router_status["primary_model"],
        fallback_models=router_status["fallback_models"],
        total_calls=stats["total_calls"],
        fallback_rate=stats["fallback_rate"],
        error_rate=stats["error_rate"],
        p50_latency_ms=stats["p50_latency_ms"],
        p95_latency_ms=stats["p95_latency_ms"],
        models=models_out,
        recent_calls=recent_calls,
    )
