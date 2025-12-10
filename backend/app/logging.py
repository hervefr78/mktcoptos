import logging as std_logging
import json
import os
import uuid
from contextvars import ContextVar
from datetime import datetime
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable to store request ID
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)

class RequestIdFilter(std_logging.Filter):
    """Inject the request ID into log records."""

    def filter(self, record: std_logging.LogRecord) -> bool:  # type: ignore[override]
        record.request_id = request_id_ctx_var.get()
        return True


class JsonFormatter(std_logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: std_logging.LogRecord) -> str:  # type: ignore[override]
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        return json.dumps(log_record)


logger = std_logging.getLogger("app")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to assign a request ID to each request."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = str(uuid.uuid4())
        token = request_id_ctx_var.set(request_id)
        logger.info("request.start", extra={"method": request.method, "path": request.url.path})
        response = await call_next(request)
        logger.info("request.end", extra={"status": response.status_code})
        response.headers["X-Request-ID"] = request_id
        request_id_ctx_var.reset(token)
        return response


def setup_logging(log_file: str = "logs/app.log") -> None:
    """Configure standard logging to emit JSON lines."""

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    handler = std_logging.FileHandler(log_file)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    std_logging.basicConfig(level=std_logging.INFO, handlers=[handler])
