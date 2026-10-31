import time
from collections import defaultdict

from app.core.errors import RateLimitedError


class InMemoryRateLimiter:
    """Sliding-window in-process rate limiter per demo user."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[int, list[float]] = defaultdict(list)

    def check(self, user_id: int) -> None:
        now = time.time()
        window_start = now - self.window_seconds
        # Clean older entries
        self.requests[user_id] = [t for t in self.requests[user_id] if t > window_start]

        if len(self.requests[user_id]) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - self.requests[user_id][0])) + 1
            raise RateLimitedError(
                message=f"Too many requests. Please wait {retry_after} seconds.",
                retry_after_s=max(1, retry_after),
            )

        self.requests[user_id].append(now)


user_rate_limiter = InMemoryRateLimiter(max_requests=40, window_seconds=60)
