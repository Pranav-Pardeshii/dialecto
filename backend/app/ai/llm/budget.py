import time
from typing import Any


class TokenBudgetManager:
    """In-process token bucket rate limiter per model."""

    def __init__(self, default_tokens_per_minute: int = 20000) -> None:
        self.default_capacity = float(default_tokens_per_minute)
        self.refill_rate = self.default_capacity / 60.0  # tokens per second
        self._buckets: dict[str, dict[str, float]] = {}

    def _get_bucket(self, model: str) -> dict[str, float]:
        if model not in self._buckets:
            self._buckets[model] = {
                "tokens": self.default_capacity,
                "last_update": time.monotonic(),
            }
        return self._buckets[model]

    def _refill(self, model: str) -> None:
        bucket = self._get_bucket(model)
        now = time.monotonic()
        elapsed = now - bucket["last_update"]
        bucket["last_update"] = now
        bucket["tokens"] = min(
            self.default_capacity, bucket["tokens"] + (elapsed * self.refill_rate)
        )

    def can_consume(self, model: str, estimated_tokens: int) -> bool:
        """Checks if there are enough tokens without consuming."""
        self._refill(model)
        bucket = self._get_bucket(model)
        return bucket["tokens"] >= estimated_tokens

    def consume(self, model: str, tokens: int) -> None:
        """Deducts tokens from the bucket."""
        self._refill(model)
        bucket = self._get_bucket(model)
        bucket["tokens"] = max(0.0, bucket["tokens"] - tokens)

    def get_status(self, model: str) -> dict[str, Any]:
        """Telemetry representation."""
        self._refill(model)
        bucket = self._get_bucket(model)
        available = round(bucket["tokens"])
        return {
            "capacity": int(self.default_capacity),
            "available": available,
            "pct_remaining": round((available / self.default_capacity) * 100, 1),
        }
