from pydantic import BaseModel, Field


class ModelBreakerStatus(BaseModel):
    model: str
    state: str
    failure_count: int
    seconds_until_reset: float


class ModelTokenBudgetStatus(BaseModel):
    capacity: int
    available: int
    pct_remaining: float


class ModelStatusOut(BaseModel):
    model: str
    is_primary: bool
    circuit_breaker: ModelBreakerStatus
    token_budget: ModelTokenBudgetStatus
    calls: int = 0
    errors: int = 0
    avg_latency_ms: int = 0
    tokens_consumed: int = 0


class RecentCallOut(BaseModel):
    purpose: str
    model: str
    latency_ms: int
    status: str
    fallback_used: bool
    tokens: int
    created_at: str


class LLMStatsResponse(BaseModel):
    primary_model: str
    fallback_models: list[str]
    total_calls: int = Field(..., ge=0)
    fallback_rate: float = Field(..., ge=0.0, le=100.0)
    error_rate: float = Field(..., ge=0.0, le=100.0)
    p50_latency_ms: int = Field(..., ge=0)
    p95_latency_ms: int = Field(..., ge=0)
    models: list[ModelStatusOut]
    recent_calls: list[RecentCallOut]
