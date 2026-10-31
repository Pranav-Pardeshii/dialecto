import structlog
from groq import AsyncGroq

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

_groq_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    """Singleton getter for AsyncGroq client."""
    global _groq_client
    if _groq_client is None:
        settings = get_settings()
        _groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _groq_client


async def verify_available_models() -> list[str]:
    """Queries Groq models API and verifies which configured models are available.

    Logs warnings for any configured models not found in the account/API.
    """
    settings = get_settings()
    configured_models = [settings.LLM_PRIMARY_MODEL] + settings.fallback_models_list
    available_model_ids: list[str] = []

    try:
        client = get_groq_client()
        response = await client.models.list()
        available_model_ids = [m.id for m in response.data]
        logger.info("groq_models_fetched", count=len(available_model_ids))

        for model in configured_models:
            if model not in available_model_ids:
                logger.warning(
                    "configured_model_not_found_in_groq",
                    model=model,
                    available_sample=available_model_ids[:5],
                )
    except Exception as exc:
        logger.warning("groq_model_verification_failed", error=str(exc))
        # Keep configured models in case of transient network issue at startup
        return configured_models

    return available_model_ids
