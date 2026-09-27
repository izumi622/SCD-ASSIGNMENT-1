from app.core.config import get_settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.llm import LLMTriage
from app.providers.triage.ollama import OllamaTriage
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


def get_triage_provider(provider_name: str | None = None) -> TriageProvider:
    """Factory function returning the configured TriageProvider instance."""
    settings = get_settings()
    name = (provider_name or settings.TRIAGE_PROVIDER).lower()

    if name in ("llm", "groq", "llm:groq"):
        return LLMTriage()
    elif name in ("ollama", "llm:ollama"):
        return OllamaTriage()
    elif name in ("rules", "rule_based"):
        return RuleBasedTriage()
    elif name in ("simulated", "fake"):
        return SimulatedTriage()
    else:
        # Default fallback
        return RuleBasedTriage()
