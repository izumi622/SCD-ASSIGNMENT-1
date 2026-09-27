"""
Triage provider interface and exports.
"""

from app.providers.triage.base import TriageProvider, TriageResult
from app.providers.triage.factory import get_triage_provider
from app.providers.triage.llm import LLMTriage
from app.providers.triage.ollama import OllamaTriage
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage

__all__ = [
    "TriageProvider",
    "TriageResult",
    "get_triage_provider",
    "RuleBasedTriage",
    "SimulatedTriage",
    "LLMTriage",
    "OllamaTriage",
]
