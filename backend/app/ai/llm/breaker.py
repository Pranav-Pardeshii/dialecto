import time
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """In-process circuit breaker for an LLM model."""

    def __init__(
        self, model_name: str, max_failures: int = 3, reset_timeout_s: float = 60.0
    ) -> None:
        self.model_name = model_name
        self.max_failures = max_failures
        self.reset_timeout_s = reset_timeout_s
        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.reset_at: float = 0.0

    def is_open(self) -> bool:
        """Returns True if breaker is open and should not be used."""
        now = time.monotonic()
        if self.state == CircuitState.OPEN:
            if now >= self.reset_at:
                logger.info("circuit_breaker_half_open", model=self.model_name)
                self.state = CircuitState.HALF_OPEN
                return False
            return True
        return False

    def record_success(self) -> None:
        """Records a successful call and closes/resets breaker."""
        if self.state != CircuitState.CLOSED:
            logger.info("circuit_breaker_closed", model=self.model_name)
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.reset_at = 0.0

    def record_failure(self, retry_after_s: float | None = None) -> None:
        """Records a failure. Trips immediately on rate limit or after max_failures."""
        now = time.monotonic()
        self.failure_count += 1
        self.last_failure_time = now

        cooldown = retry_after_s if retry_after_s and retry_after_s > 0 else self.reset_timeout_s

        if (
            retry_after_s is not None
            or self.failure_count >= self.max_failures
            or self.state == CircuitState.HALF_OPEN
        ):
            self.state = CircuitState.OPEN
            self.reset_at = now + cooldown
            logger.warning(
                "circuit_breaker_tripped_open",
                model=self.model_name,
                failure_count=self.failure_count,
                cooldown_s=cooldown,
            )

    def get_status(self) -> dict[str, Any]:
        """Telemetry representation."""
        now = time.monotonic()
        remaining = max(0.0, self.reset_at - now) if self.state == CircuitState.OPEN else 0.0
        return {
            "model": self.model_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "seconds_until_reset": round(remaining, 1),
        }
