import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from payment_lab.core.errors import PaymentLabException

logger = structlog.get_logger()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = corr_id
        structlog.contextvars.bind_contextvars(correlation_id=corr_id)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response
        except Exception as exc:
            # Let custom exception handler catch it
            raise exc


async def payment_lab_exception_handler(request: Request, exc: PaymentLabException) -> JSONResponse:
    corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    details = [d.model_dump() for d in exc.details] if exc.details else None
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "correlation_id": corr_id,
                "details": details,
            }
        },
        headers={"X-Correlation-ID": corr_id},
    )

