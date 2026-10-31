
from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = "ok"


class ReadyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = "ok"
    database: str = "connected"
    environment: str
    primary_model: str
    available_fallback_models: list[str]
