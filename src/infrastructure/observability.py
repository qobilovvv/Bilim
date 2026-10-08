import json
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "method", "path", "status", "duration_ms"):
            if hasattr(record, field):
                data[field] = getattr(record, field)
        return json.dumps(data)


def configure_logging():
    logger = logging.getLogger("bilim")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


# Bounded by route templates and status codes, not user IDs or arbitrary paths.
request_metrics = defaultdict(lambda: {"requests": 0, "total_duration_ms": 0.0})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        request_id = (
            supplied
            if 0 < len(supplied) <= 64
            and supplied.isascii()
            and all(char.isalnum() or char in "-_" for char in supplied)
            else uuid.uuid4().hex
        )
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = round((time.perf_counter() - started) * 1000, 3)
            route = request.scope.get("route")
            path = getattr(route, "path", "unmatched")
            method = (
                request.method
                if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
                else "OTHER"
            )
            metrics = request_metrics[(method, path, status)]
            metrics["requests"] += 1
            metrics["total_duration_ms"] += duration
            logging.getLogger("bilim.requests").log(
                logging.ERROR if status >= 500 else logging.INFO,
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "status": status,
                    "duration_ms": duration,
                },
            )
