import asyncio
import logging
import signal
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import async_engine
from app.core.logging import request_id_ctx, setup_logging
from app.providers.cache import get_cache_provider
from app.providers.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL
from app.routes.complaints import router as complaints_router
from app.routes.probes import router as probes_router

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("civicpulse")

# Tracking active in-flight requests for graceful drain
active_requests: int = 0
is_shutting_down: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager handling startup, graceful drain, and cleanup on SIGTERM."""
    global is_shutting_down
    logger.info(
        f"CivicPulse backend starting in {settings.ENVIRONMENT} mode. "
        f"Active triage provider: {settings.TRIAGE_PROVIDER}"
    )

    # Register signal handler for SIGTERM where supported (Unix/Linux container environments)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(handle_graceful_shutdown(s)),
            )
        except (NotImplementedError, AttributeError):
            # Windows does not support loop.add_signal_handler for SIGTERM
            pass

    yield

    # Shutdown sequence
    is_shutting_down = True
    logger.info("Graceful shutdown initiated. Draining in-flight requests...")

    # Wait for in-flight requests to complete (up to 15 seconds)
    drain_timeout = 15.0
    start_drain = time.time()
    while active_requests > 0 and (time.time() - start_drain) < drain_timeout:
        await asyncio.sleep(0.1)

    logger.info(f"Drain complete. Remaining active requests: {active_requests}")

    # Close Redis client
    cache = await get_cache_provider()
    await cache.close()

    # Dispose database connection pool
    await async_engine.dispose()
    logger.info("Database and Redis connections closed. Process terminating cleanly.")


async def handle_graceful_shutdown(sig: signal.Signals) -> None:
    logger.info(f"Received signal {sig.name}. Triggering graceful shutdown.")


app = FastAPI(
    title="CivicPulse API",
    description="Municipal Complaint Intake, AI Triage, and Operations Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware for local frontend development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Cache", "Retry-After"],
)


@app.middleware("http")
async def logging_and_metrics_middleware(request: Request, call_next):
    """Propagates X-Request-ID, logs requests in structured JSON, and records Prometheus metrics."""
    global active_requests

    # Reject new requests if shutting down with 503
    if is_shutting_down and request.url.path not in ("/health", "/ready"):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Server is shutting down"},
        )

    active_requests += 1

    # Extract or generate X-Request-ID
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_ctx.set(req_id)

    start_time = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = req_id
        return response
    except Exception as exc:
        logger.exception(
            f"Unhandled exception processing {request.method} {request.url.path}: {exc}"
        )
        raise
    finally:
        active_requests -= 1
        duration = time.perf_counter() - start_time
        path = request.url.path

        # Record metrics (normalize path to avoid high cardinality)
        metric_endpoint = path
        if path.startswith("/api/complaints/") and path.endswith("/status"):
            metric_endpoint = "/api/complaints/{id}/status"
        elif path.startswith("/api/complaints/") and len(path.split("/")) == 4:
            metric_endpoint = "/api/complaints/{id}"

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=metric_endpoint,
            status_code=status_code,
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            endpoint=metric_endpoint,
        ).observe(duration)

        logger.info(
            f"{request.method} {path} completed with {status_code} in {duration * 1000:.2f}ms",
            extra={"status_code": status_code, "latency_ms": int(duration * 1000)},
        )
        request_id_ctx.reset(token)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Converts 422 to 400 with structured field-level error bodies as specified by §2.2."""
    formatted_errors = []
    for error in exc.errors():
        formatted_errors.append(
            {
                "loc": [str(x) for x in error.get("loc", [])],
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
        )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": formatted_errors},
        headers={"X-Request-ID": request_id_ctx.get() or ""},
    )


# Include API Routers
app.include_router(complaints_router)
app.include_router(probes_router)
