import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

# Context variable to hold the request_id across async coroutines
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class JSONLogFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects to stdout."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get() or getattr(record, "request_id", ""),
        }

        # Include custom extra attributes if passed
        for key in (
            "complaint_id",
            "provider",
            "error_class",
            "latency_ms",
            "cached",
            "status_code",
        ):
            if hasattr(record, key):
                log_obj[key] = getattr(record, key)

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging(log_level: str = "INFO") -> None:
    """Configures structured JSON logging to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Suppress overly verbose third-party loggers
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False
