import asyncio
import json
import time
from typing import Any, TypeVar

import structlog
from groq import (
    APIConnectionError,
    APIError,
    AsyncGroq,
    InternalServerError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.ai.llm.breaker import CircuitBreaker
from app.ai.llm.budget import TokenBudgetManager
from app.ai.llm.client import get_groq_client
from app.ai.llm.recorder import recorder
from app.core.config import get_settings
from app.core.errors import AppError
from app.models.entities import LLMCallStatusEnum
from app.schemas.practice import AIFallbackMeta

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(AppError):
    def __init__(
        self, message: str = "All configured language models are currently unavailable"
    ) -> None:
        super().__init__(
            code="ai_unavailable",
            message=message,
            status_code=503,
            details={},
        )


class LLMRouter:
    """Resilient router for Groq LLM calls with circuit breakers, token budgets, and graceful fallbacks."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.primary_model = self.settings.LLM_PRIMARY_MODEL
        self.fallback_models = self.settings.fallback_models_list
        self.breakers: dict[str, CircuitBreaker] = {}
        self.budget_manager = TokenBudgetManager(self.settings.TOKEN_BUDGET_PER_MINUTE)

        # Initialize circuit breakers for all configured models
        for model in [self.primary_model] + self.fallback_models:
            self.breakers[model] = CircuitBreaker(
                model_name=model,
                max_failures=self.settings.CIRCUIT_BREAKER_MAX_FAILURES,
                reset_timeout_s=self.settings.CIRCUIT_BREAKER_RESET_SECS,
            )

    def _get_breaker(self, model: str) -> CircuitBreaker:
        if model not in self.breakers:
            self.breakers[model] = CircuitBreaker(
                model_name=model,
                max_failures=self.settings.CIRCUIT_BREAKER_MAX_FAILURES,
                reset_timeout_s=self.settings.CIRCUIT_BREAKER_RESET_SECS,
            )
        return self.breakers[model]

    async def complete(
        self,
        purpose: str,
        messages: list[dict[str, str]],
        schema: type[T] | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.2,
        timeout: float | None = None,
        reasoning_effort: str | None = None,
    ) -> tuple[Any, AIFallbackMeta]:
        """Routes a prompt completion through the resilient model chain."""
        client: AsyncGroq = get_groq_client()
        timeout_s = timeout if timeout is not None else self.settings.LLM_TIMEOUT_S
        chain = [self.primary_model] + self.fallback_models

        # Estimate tokens (approx 4 chars per token + max_tokens reserve)
        prompt_chars = sum(len(m.get("content", "")) for m in messages)
        estimated_tokens = (prompt_chars // 4) + max_tokens

        last_error_class: str | None = None

        for attempt_idx, model in enumerate(chain, start=1):
            fallback_used = model != self.primary_model
            breaker = self._get_breaker(model)

            # 1. Skip if circuit breaker is open
            if breaker.is_open():
                logger.info("llm_model_skipped_breaker_open", model=model, purpose=purpose)
                continue

            # 2. Skip if token budget is exhausted
            if not self.budget_manager.can_consume(model, estimated_tokens):
                logger.warning(
                    "llm_model_skipped_budget_exhausted",
                    model=model,
                    estimated=estimated_tokens,
                    purpose=purpose,
                )
                continue

            # 3. Call the model with timeout
            start_time = time.monotonic()
            response_kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if schema is not None:
                response_kwargs["response_format"] = {"type": "json_object"}
            if reasoning_effort is not None and ("gpt-oss" in model or "deepseek" in model):
                response_kwargs["reasoning_effort"] = reasoning_effort

            try:
                async with asyncio.timeout(timeout_s):
                    response = await client.chat.completions.create(**response_kwargs)

                latency_ms = int((time.monotonic() - start_time) * 1000)
                raw_text = response.choices[0].message.content or ""
                p_tokens = response.usage.prompt_tokens if response.usage else estimated_tokens
                c_tokens = response.usage.completion_tokens if response.usage else 50
                self.budget_manager.consume(model, p_tokens + c_tokens)

                # Validate schema if required
                parsed_result: Any = raw_text
                if schema is not None:
                    try:
                        parsed_json = json.loads(raw_text)
                        parsed_result = schema.model_validate(parsed_json)
                    except (json.JSONDecodeError, ValidationError) as parse_err:
                        # Attempt one repair retry on the same model
                        logger.warning(
                            "llm_schema_validation_failed_attempting_repair",
                            model=model,
                            purpose=purpose,
                            error=str(parse_err),
                        )
                        repair_messages = list(messages) + [
                            {"role": "assistant", "content": raw_text},
                            {
                                "role": "user",
                                "content": (
                                    f"Your previous response had validation errors: {parse_err}. "
                                    f"Return ONLY a valid JSON object matching the required schema."
                                ),
                            },
                        ]
                        async with asyncio.timeout(timeout_s):
                            repair_resp = await client.chat.completions.create(
                                model=model,
                                messages=repair_messages,
                                max_tokens=max_tokens,
                                temperature=0.1,
                                response_format={"type": "json_object"},
                            )
                        repair_text = repair_resp.choices[0].message.content or ""
                        parsed_json = json.loads(repair_text)
                        parsed_result = schema.model_validate(parsed_json)

                # Call succeeded and schema parsed
                breaker.record_success()
                recorder.record(
                    {
                        "purpose": purpose,
                        "model": model,
                        "attempt_no": attempt_idx,
                        "fallback_used": fallback_used,
                        "latency_ms": latency_ms,
                        "prompt_tokens": p_tokens,
                        "completion_tokens": c_tokens,
                        "status": LLMCallStatusEnum.OK,
                        "error_class": None,
                    }
                )

                return parsed_result, AIFallbackMeta(
                    used=True,
                    model=model,
                    fallback=fallback_used,
                )

            except RateLimitError as rle:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                last_error_class = "RateLimitError"
                breaker.record_failure(retry_after_s=20.0)
                recorder.record(
                    {
                        "purpose": purpose,
                        "model": model,
                        "attempt_no": attempt_idx,
                        "fallback_used": fallback_used,
                        "latency_ms": latency_ms,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "status": LLMCallStatusEnum.RATE_LIMITED,
                        "error_class": "RateLimitError",
                    }
                )
                logger.warning("llm_rate_limit_tripped", model=model, error=str(rle))
                continue

            except TimeoutError:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                last_error_class = "TimeoutError"
                breaker.record_failure()
                recorder.record(
                    {
                        "purpose": purpose,
                        "model": model,
                        "attempt_no": attempt_idx,
                        "fallback_used": fallback_used,
                        "latency_ms": latency_ms,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "status": LLMCallStatusEnum.TIMEOUT,
                        "error_class": "TimeoutError",
                    }
                )
                logger.warning("llm_call_timeout", model=model, timeout_s=timeout_s)
                continue

            except (APIConnectionError, InternalServerError, APIError) as api_err:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                last_error_class = api_err.__class__.__name__
                breaker.record_failure()
                recorder.record(
                    {
                        "purpose": purpose,
                        "model": model,
                        "attempt_no": attempt_idx,
                        "fallback_used": fallback_used,
                        "latency_ms": latency_ms,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "status": LLMCallStatusEnum.ERROR,
                        "error_class": last_error_class,
                    }
                )
                logger.warning("llm_api_error", model=model, error=str(api_err))
                continue

            except Exception as exc:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                last_error_class = exc.__class__.__name__
                breaker.record_failure()
                recorder.record(
                    {
                        "purpose": purpose,
                        "model": model,
                        "attempt_no": attempt_idx,
                        "fallback_used": fallback_used,
                        "latency_ms": latency_ms,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "status": LLMCallStatusEnum.ERROR,
                        "error_class": last_error_class,
                    }
                )
                logger.error("llm_unexpected_failure", model=model, error=str(exc))
                continue

        # If we exhausted all models in the chain
        logger.critical(
            "llm_all_models_failed",
            purpose=purpose,
            last_error=last_error_class,
        )
        raise LLMUnavailableError(
            f"All configured language models failed for purpose '{purpose}'. Last error: {last_error_class}"
        )

    def get_status(self) -> dict[str, Any]:
        """Provides combined status of circuit breakers and token budgets for telemetry."""
        models_status: list[dict[str, Any]] = []
        for model in [self.primary_model] + self.fallback_models:
            breaker = self._get_breaker(model)
            budget = self.budget_manager.get_status(model)
            models_status.append(
                {
                    "model": model,
                    "is_primary": model == self.primary_model,
                    "circuit_breaker": breaker.get_status(),
                    "token_budget": budget,
                }
            )
        return {
            "primary_model": self.primary_model,
            "fallback_models": self.fallback_models,
            "models": models_status,
        }


# Singleton LLMRouter
router = LLMRouter()
