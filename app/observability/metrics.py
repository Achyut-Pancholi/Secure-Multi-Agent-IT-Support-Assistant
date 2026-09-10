from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter
from fastapi.responses import Response
import time

# Prometheus Metrics
SUPPORT_REQUESTS_TOTAL = Counter(
    "support_requests_total",
    "Total number of support requests received",
    ["status"]
)

REQUEST_PROCESSING_SECONDS = Histogram(
    "request_processing_seconds",
    "Time taken to process support requests",
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

metrics_router = APIRouter()

@metrics_router.get("/metrics")
async def get_metrics():
    """
    Expose Prometheus metrics endpoint.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

class MetricsTimer:
    """Context manager to easily time request duration and count success/errors."""
    def __init__(self):
        self.start_time = 0
        self.status = "error"

    def __enter__(self):
        self.start_time = time.time()
        return self

    def success(self):
        self.status = "success"

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        SUPPORT_REQUESTS_TOTAL.labels(status=self.status).inc()
        REQUEST_PROCESSING_SECONDS.observe(duration)

