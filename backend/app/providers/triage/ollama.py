import json
import logging
import re
from typing import Optional

import httpx

from app.core.config import get_settings
from app.providers.triage.base import TriageResult
from app.providers.triage.llm import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class OllamaTriage:
    """Offline triage provider calling a local Ollama container."""

    name: str = "llm:ollama"

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout

    def triage(self, text: str, location: str) -> TriageResult:
        user_message = (
            f"{SYSTEM_PROMPT}\n\n"
            f"<untrusted_complaint_location>\n{location}\n</untrusted_complaint_location>\n"
            f"<untrusted_complaint_text>\n{text}\n</untrusted_complaint_text>\n"
            "Respond strictly in valid JSON matching the schema."
        )

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": user_message,
                    "format": "json",
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw_response = data.get("response", "")

            cleaned_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip())
            parsed_json = json.loads(cleaned_content)
            return TriageResult.model_validate(parsed_json)
