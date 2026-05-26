"""
Middleware: request logging, correlation IDs, Prometheus metrics.
"""

from __future__ import annotations

import time

from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import generate_request_id, get_logger, request_id_var

logger = get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
LLM_INFERENCE_LATENCY = Histogram(
    "llm_inference_duration_seconds",
    "LLM inference duration",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = generate_request_id()
        request_id_var.set(request_id)

        start = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration*1000:.1f}ms"

            # Metrics
            endpoint = _normalize_path(path)
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

            logger.info(
                "Request completed",
                method=method,
                path=path,
                status=response.status_code,
                duration_ms=round(duration * 1000, 1),
            )
            return response

        except Exception as e:
            duration = time.perf_counter() - start
            logger.error(
                "Request failed",
                method=method,
                path=path,
                error=str(e),
                duration_ms=round(duration * 1000, 1),
            )
            raise


def _normalize_path(path: str) -> str:
    """Normalize path for metrics labels (replace UUIDs with :id)."""
    import re
    return re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        ":id",
        path,
    )
