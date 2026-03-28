import logging
import sys
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


def configure_logging() -> None:
    root_logger = logging.getLogger()

    if root_logger.handlers:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("app")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        request.state.request_id = request_id

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            logger.info(
                "request_id=%s method=%s path=%s status_code=%s duration_ms=%s client=%s",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                request.client.host if request.client else None,
            )

            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "request_id=%s method=%s path=%s status_code=500 duration_ms=%s client=%s unhandled_exception=true",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
                request.client.host if request.client else None,
            )
            raise