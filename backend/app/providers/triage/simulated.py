import hashlib

from app.providers.triage.base import TriageResult
from app.providers.triage.rules import RuleBasedTriage


class SimulatedTriageError(Exception):
    """Raised when SimulatedTriage is configured or triggered to fail."""

    pass


class SimulatedTimeoutError(TimeoutError):
    """Simulated network timeout for testing retries and fallback."""

    pass


class SimulatedRateLimitError(Exception):
    """Simulated 429 rate limit error."""

    pass


class SimulatedTriage:
    """Deterministic fake triage provider for CI/CD and testing.
    Supports deterministic seeded output and configurable failure injection.
    """

    name: str = "simulated"

    def __init__(self, failure_mode: str = "none") -> None:
        self.failure_mode = failure_mode
        self._rules_fallback = RuleBasedTriage()

    def set_failure_mode(self, mode: str) -> None:
        self.failure_mode = mode

    def triage(self, text: str, location: str) -> TriageResult:
        # Failure injection based on mode or trigger tokens in text
        if self.failure_mode == "always_raise" or "__INJECT_ERROR__" in text:
            raise SimulatedTriageError("Simulated provider failure triggered")

        if self.failure_mode == "timeout" or "__INJECT_TIMEOUT__" in text:
            raise SimulatedTimeoutError("Simulated provider call timed out after 10s")

        if self.failure_mode == "rate_limit" or "__INJECT_429__" in text:
            raise SimulatedRateLimitError("Simulated upstream 429 Too Many Requests")

        if self.failure_mode == "malformed" or "__INJECT_MALFORMED__" in text:
            # Returns an invalid category or missing field by raising or returning garbage
            raise ValueError("Malformed JSON payload received from simulated provider")

        # Deterministic result derived from content hash and rule-based heuristics
        rule_result = self._rules_fallback.triage(text, location)

        # Stable confidence based on text hash
        text_hash = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        stable_confidence = 0.80 + ((text_hash % 20) / 100.0)

        return TriageResult(
            category=rule_result.category,
            priority=rule_result.priority,
            summary=rule_result.summary,
            confidence=round(stable_confidence, 2),
        )
