import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.database import async_engine
from app.providers.cache import get_cache_provider
from app.providers.metrics import get_metrics_text

router = APIRouter(tags=["Probes & Metrics"])
logger = logging.getLogger(__name__)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Indicates process is alive. Deliberately does NOT touch database or external services.",
)
async def health_liveness() -> dict[str, str]:
    """Kubernetes liveness probe. Fails only if the process itself is dead or deadlocked."""
    return {"status": "healthy"}


@router.get(
    "/ready",
    summary="Readiness Probe",
    description="200 only if PostgreSQL and Redis are both reachable; 503 naming the failed dependency.",
)
async def readiness_probe(response: Response) -> dict[str, str]:
    """Kubernetes readiness probe. Removes pod from Service routing if any backing service is unavailable."""
    failed_dependencies: list[str] = []

    # 1. Check PostgreSQL reachability
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error(f"Readiness check failed for PostgreSQL: {exc}")
        failed_dependencies.append("postgres")

    # 2. Check Redis reachability
    try:
        cache = await get_cache_provider()
        r = await cache.get_redis()
        if r is None:
            failed_dependencies.append("redis")
        else:
            await r.ping()
    except Exception as exc:
        logger.error(f"Readiness check failed for Redis: {exc}")
        failed_dependencies.append("redis")

    if failed_dependencies:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        failed_str = ", ".join(failed_dependencies)
        return {
            "status": "unready",
            "failed_dependency": failed_str,
            "detail": f"Backing service(s) unavailable: {failed_str}",
        }

    return {"status": "ready"}


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Exposes Prometheus text format metrics: request count, request latency, triage latency, fallback counter.",
)
async def prometheus_metrics() -> Response:
    """Returns metrics in Prometheus text format."""
    return Response(
        content=get_metrics_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
