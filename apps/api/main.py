import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import structlog
from payment_lab.core.config import settings
from payment_lab.core.errors import PaymentLabException
from payment_lab.core.logging import setup_logging
from payment_lab.db.session import init_db
from apps.api.middleware import CorrelationIdMiddleware, payment_lab_exception_handler
from apps.api.routers import (
    analytics,
    health,
    payments,
    reconciliation,
    refunds,
    sentinelqa,
    webhooks,
)

setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Initializing database schema...")
    await init_db()
    logger.info("Database schema initialized.")
    yield


app = FastAPI(
    title="SentinelQA - Payment Lab API",
    version="0.1.0",
    description="Simulated Digital Payment System with built-in Defect Injections and QA Instrumentation",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(CorrelationIdMiddleware)

# Custom Exception Handlers
app.add_exception_handler(PaymentLabException, payment_lab_exception_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    corr_id = getattr(request.state, "correlation_id", "req-validation-err")
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []) if loc != "body")
        details.append({"field": field or "body", "issue": error.get("msg", "Validation error")})

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "correlation_id": corr_id,
                "details": details,
            }
        },
        headers={"X-Correlation-ID": corr_id},
    )


# Include Routers
app.include_router(health.router)
app.include_router(payments.router, prefix=settings.API_PREFIX)
app.include_router(refunds.router, prefix=settings.API_PREFIX)
app.include_router(webhooks.router, prefix=settings.API_PREFIX)
app.include_router(reconciliation.router, prefix=settings.API_PREFIX)
app.include_router(sentinelqa.router, prefix=settings.API_PREFIX)
app.include_router(analytics.router, prefix=settings.API_PREFIX)

STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "static"))
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/dashboard", include_in_schema=False)
    async def serve_dashboard():
        index_file = os.path.join(STATIC_DIR, "index.html")
        return FileResponse(index_file)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host=settings.HOST, port=settings.PORT, reload=True)

