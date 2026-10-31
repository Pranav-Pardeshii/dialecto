from typing import Any

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.headers = headers or {}
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None):
        super().__init__(code="not_found", message=message, status_code=404, details=details)


class UnknownUserError(AppError):
    def __init__(self, message: str = "Unknown or missing demo user id"):
        super().__init__(code="unknown_user", message=message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(code="forbidden", message=message, status_code=403)


class ConflictError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(code=code, message=message, status_code=409, details=details)


class RateLimitedError(AppError):
    def __init__(self, message: str = "Rate limit exceeded", retry_after_s: int = 20):
        super().__init__(
            code="rate_limited",
            message=message,
            status_code=429,
            headers={"Retry-After": str(retry_after_s)},
        )


class AIUnavailableError(AppError):
    def __init__(self, message: str = "The tutor is busy right now. Please try again in a moment."):
        super().__init__(code="ai_unavailable", message=message, status_code=503)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "app_error",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
    )
    content: dict[str, Any] = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id,
        }
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers,
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("unhandled_error", exc_info=exc, request_id=request_id)
    content: dict[str, Any] = {
        "error": {
            "code": "internal_error",
            "message": "An unexpected server error occurred.",
            "details": {},
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=500, content=content)
