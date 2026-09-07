import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom attributes if present
        for key in [
            "request_id",
            "user_id",
            "api_key_id",
            "model",
            "backend",
            "duration_ms",
            "status_code",
            "client_ip",
            "tokens",
        ]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Setup root structured logger."""
    logger = logging.getLogger("ai_gateway")
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    # Configure uvicorn loggers
    logging.getLogger("uvicorn.access").handlers = logger.handlers
    logging.getLogger("uvicorn.error").handlers = logger.handlers

    return logger


logger = setup_logging()
