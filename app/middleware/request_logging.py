from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger
from app.core.metrics import metrics


logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id

        started_at = perf_counter()

        try:
            response = await call_next(request)

        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 3)

            metrics.record_request(
                duration_ms=duration_ms,
                is_error=True,
            )

            logger.exception(
                "request_failed request_id=%s method=%s path=%s duration_ms=%s",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )

            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 3)
        is_error = response.status_code >= 500

        metrics.record_request(
            duration_ms=duration_ms,
            is_error=is_error,
        )

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_completed request_id=%s method=%s path=%s status_code=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response