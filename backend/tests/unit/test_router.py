from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from groq import RateLimitError
from pydantic import BaseModel

from app.ai.llm.router import LLMRouter, LLMUnavailableError


class SampleOutput(BaseModel):
    message: str
    score: int


def _mock_response(content: str, prompt_tokens: int = 10, completion_tokens: int = 5) -> MagicMock:
    resp = MagicMock()
    choice = MagicMock()
    choice.message.content = content
    resp.choices = [choice]
    resp.usage.prompt_tokens = prompt_tokens
    resp.usage.completion_tokens = completion_tokens
    return resp


@pytest.mark.asyncio
async def test_router_success_with_schema() -> None:
    router = LLMRouter()
    valid_json = '{"message": "Hello world", "score": 95}'

    with patch("app.ai.llm.router.get_groq_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = _mock_response(valid_json)
        mock_get_client.return_value = mock_client

        result, meta = await router.complete(
            purpose="unit_test",
            messages=[{"role": "user", "content": "test"}],
            schema=SampleOutput,
        )

        assert isinstance(result, SampleOutput)
        assert result.message == "Hello world"
        assert result.score == 95
        assert not meta.fallback


@pytest.mark.asyncio
async def test_router_repair_retry_on_invalid_json() -> None:
    router = LLMRouter()
    invalid_json = "This is not json"
    valid_json = '{"message": "Repaired", "score": 100}'

    with patch("app.ai.llm.router.get_groq_client") as mock_get_client:
        mock_client = AsyncMock()
        # First call fails schema validation, second call (repair) succeeds
        mock_client.chat.completions.create.side_effect = [
            _mock_response(invalid_json),
            _mock_response(valid_json),
        ]
        mock_get_client.return_value = mock_client

        result, meta = await router.complete(
            purpose="repair_test",
            messages=[{"role": "user", "content": "test"}],
            schema=SampleOutput,
        )

        assert isinstance(result, SampleOutput)
        assert result.message == "Repaired"
        assert result.score == 100
        assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_router_fallback_on_rate_limit() -> None:
    router = LLMRouter()
    valid_json = '{"message": "Fallback success", "score": 88}'

    with patch("app.ai.llm.router.get_groq_client") as mock_get_client:
        mock_client = AsyncMock()
        # Primary model raises RateLimitError; fallback model succeeds
        mock_response_req = MagicMock()
        rle = RateLimitError(
            message="Rate limit reached",
            response=mock_response_req,
            body={"error": {"message": "Rate limit"}},
        )

        mock_client.chat.completions.create.side_effect = [
            rle,
            _mock_response(valid_json),
        ]
        mock_get_client.return_value = mock_client

        result, meta = await router.complete(
            purpose="fallback_test",
            messages=[{"role": "user", "content": "test"}],
            schema=SampleOutput,
        )

        assert isinstance(result, SampleOutput)
        assert result.message == "Fallback success"
        assert meta.fallback is True
        # Breaker on primary model must now be OPEN
        assert router.breakers[router.primary_model].is_open()


@pytest.mark.asyncio
async def test_router_all_models_unavailable_raises_error() -> None:
    router = LLMRouter()

    with patch("app.ai.llm.router.get_groq_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("Network error")
        mock_get_client.return_value = mock_client

        with pytest.raises(LLMUnavailableError):
            await router.complete(
                purpose="failure_test",
                messages=[{"role": "user", "content": "test"}],
                schema=SampleOutput,
            )
