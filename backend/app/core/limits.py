import time
from collections import defaultdict

from app.core.errors import RateLimitedError


class InMemoryRateLimiter:
    """Sliding-window in-process rate limiter per identifier (user_id or IP)."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def check(self, identifier: str | int) -> None:
        key = str(identifier)
        now = time.time()
        window_start = now - self.window_seconds
        # Clean older entries
        self.requests[key] = [t for t in self.requests[key] if t > window_start]

        if len(self.requests[key]) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - self.requests[key][0])) + 1
            raise RateLimitedError(
                message=f"Too many requests. Please wait {retry_after} seconds.",
                retry_after_s=max(1, retry_after),
            )

        self.requests[key].append(now)


user_rate_limiter = InMemoryRateLimiter(max_requests=40, window_seconds=60)
speech_rate_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
teachback_rate_limiter = InMemoryRateLimiter(max_requests=20, window_seconds=60)
