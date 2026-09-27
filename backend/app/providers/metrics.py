from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

# Custom registry to prevent collisions and keep metrics clean
REGISTRY = CollectorRegistry(auto_describe=True)

# Prometheus Metrics as required by Page 6:
# request count, request latency histogram, triage latency, fallback counter
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

TRIAGE_DURATION_SECONDS = Histogram(
    "triage_duration_seconds",
    "AI triage processing latency in seconds",
    ["provider"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
    registry=REGISTRY,
)

TRIAGE_FALLBACK_TOTAL = Counter(
    "triage_fallback_total",
    "Total triage fallback occurrences",
    ["provider", "error_class"],
    registry=REGISTRY,
)


def get_metrics_text() -> bytes:
    """Serializes registry metrics into Prometheus text format."""
    return generate_latest(REGISTRY)
