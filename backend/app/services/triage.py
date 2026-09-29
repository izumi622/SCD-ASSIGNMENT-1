import asyncio
import hashlib
import json
import logging
import random
import time
from collections import deque
from datetime import datetime, timezone
from typing import Deque, List, Tuple

import httpx

from app.core.config import get_settings
from app.models.schemas import TriageOutcome
from app.providers.cache import CacheProvider
from app.providers.metrics import TRIAGE_DURATION_SECONDS, TRIAGE_FALLBACK_TOTAL
from app.providers.triage.base import TriageProvider, TriageResult
from app.providers.triage.factory import get_triage_provider
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedRateLimitError

logger = logging.getLogger(__name__)


def is_retryable_exception(exc: Exception) -> bool:
    """Retry once, with jitter — on timeout, 429 and 5xx only. Never retry a 400."""
    if isinstance(exc, (TimeoutError, httpx.TimeoutException, SimulatedRateLimitError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or 500 <= exc.response.status_code <= 599
    return False


class TriageService:
    """Orchestrates AI complaint triage:
    - 24h Redis content-hash caching
    - Hard 10s timeout
    - Jittered retry on retryable errors
    - Deterministic fallback to RuleBasedTriage
    - Observability and rolling outcome tracking
    """

    def __init__(
        self,
        provider: TriageProvider | None = None,
        cache: CacheProvider | None = None,
    ) -> None:
        self.settings = get_settings()
        self.provider = provider or get_triage_provider()
        self.cache = cache or CacheProvider()
        self.fallback_rules = RuleBasedTriage()
        self.recent_outcomes: Deque[TriageOutcome] = deque(maxlen=20)

    def _compute_hash(self, text: str, location: str) -> str:
        content = json.dumps([location.strip().lower(), text.strip().lower()], ensure_ascii=False)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def triage_complaint(
        self, text: str, location: str, tracking_id: str = "new"
    ) -> Tuple[TriageResult, str, int]:
        """Triages complaint text and location.
        Returns: (TriageResult, triaged_by_provider_name, latency_ms)
        """
        content_hash = self._compute_hash(text, location)

        # 1. Check Redis content-hash cache (24h TTL)
        cached_result = await self.cache.get_triage_cache(content_hash)
        if cached_result:
            cached_triage_result = TriageResult.model_validate(cached_result)
            provider_name = cached_result.get("triaged_by", self.provider.name)
            latency_ms = 0
            self.recent_outcomes.append(
                TriageOutcome(
                    provider=f"{provider_name}:cache",
                    latency_ms=0,
                    fallback=False,
                    timestamp=datetime.now(timezone.utc),
                )
            )
            return cached_triage_result, provider_name, latency_ms

        start_time = time.perf_counter()
        active_provider_name = self.provider.name
        triaged_by = active_provider_name
        is_fallback = False
        result: TriageResult | None = None

        # 2. Call provider with timeout and retry logic
        for attempt in range(self.settings.AI_MAX_RETRIES + 1):
            try:
                # Enforce hard 10-second timeout asynchronously
                result = await asyncio.wait_for(
                    asyncio.to_thread(self.provider.triage, text, location),
                    timeout=self.settings.AI_TIMEOUT_SECONDS,
                )
                result = TriageResult.model_validate(result)
                break
            except Exception as exc:
                if attempt < self.settings.AI_MAX_RETRIES and is_retryable_exception(exc):
                    # Jittered backoff (e.g. 100ms - 300ms)
                    jitter = random.uniform(0.1, 0.3)
                    logger.info(
                        "Retrying triage call after %.2fs; error_class=%s",
                        jitter,
                        type(exc).__name__,
                    )
                    await asyncio.sleep(jitter)
                    continue

                # Fallback to RuleBasedTriage
                is_fallback = True
                triaged_by = "rules:fallback"
                error_class = exc.__class__.__name__

                # One WARNING per triage fallback with complaint id, provider, error class
                logger.warning(
                    f"Triage fallback triggered: provider='{active_provider_name}', "
                    f"error='{error_class}', complaint_id='{tracking_id}'",
                    extra={
                        "complaint_id": tracking_id,
                        "provider": active_provider_name,
                        "error_class": error_class,
                    },
                )
                TRIAGE_FALLBACK_TOTAL.labels(
                    provider=active_provider_name,
                    error_class=error_class,
                ).inc()

                result = self.fallback_rules.triage(text, location)
                break

        if result is None:
            is_fallback = True
            triaged_by = "rules:fallback"
            result = self.fallback_rules.triage(text, location)

        end_time = time.perf_counter()
        latency_ms = int((end_time - start_time) * 1000)

        # Record metrics
        TRIAGE_DURATION_SECONDS.labels(provider=triaged_by).observe(latency_ms / 1000.0)

        # Track in rolling outcomes buffer
        self.recent_outcomes.append(
            TriageOutcome(
                provider=triaged_by,
                latency_ms=latency_ms,
                fallback=is_fallback,
                timestamp=datetime.now(timezone.utc),
            )
        )

        # Store in Redis 24h content-hash cache if not a fallback
        if not is_fallback and result is not None:
            cache_payload = result.model_dump()
            cache_payload["triaged_by"] = triaged_by
            await self.cache.set_triage_cache(
                content_hash, cache_payload, ttl_seconds=self.settings.TRIAGE_CACHE_TTL_SECONDS
            )

        return result, triaged_by, latency_ms

    def get_recent_outcomes(self) -> List[TriageOutcome]:
        return list(self.recent_outcomes)


# Singleton triage service instance
triage_service = TriageService()


def get_triage_service() -> TriageService:
    return triage_service
