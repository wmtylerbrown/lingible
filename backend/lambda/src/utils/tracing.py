"""Tracing configuration with performance focus."""

from typing import Optional
from aws_lambda_powertools import Tracer
from .config import get_config

# Get configuration
config = get_config()


class PerformanceTracer:
    """Performance-focused tracer with selective tracing."""

    tracer: Optional[Tracer]

    def __init__(self) -> None:
        """Initialize performance tracer."""
        tracing_config = config.get_tracing_config()

        if tracing_config["enabled"]:
            self.tracer = Tracer(service=tracing_config["service_name"])
        else:
            self.tracer = None

    def trace_method(self, method_name: str = ""):
        """Decorator to trace method execution."""
        if not self.tracer:
            return lambda func: func

        def decorator(func):
            if self.tracer:
                return self.tracer.capture_method(func)
            return func

        return decorator

    def trace_lambda(self, func):
        """Decorator to trace Lambda function."""
        if not self.tracer:
            return func

        return self.tracer.capture_lambda_handler(func)

    def add_annotation(self, key: str, value: str) -> None:
        """Add annotation to current trace."""
        if self.tracer:
            self.tracer.put_annotation(key, value)

    def add_metadata(self, key: str, value) -> None:
        """Add metadata to current trace."""
        if self.tracer:
            self.tracer.put_metadata(key, value)

    def trace_database_operation(self, operation: str, table: str):
        """Trace database operations."""
        if not self.tracer:
            return lambda func: func

        def decorator(func):
            def wrapper(*args, **kwargs):
                if self.tracer and self.tracer.provider:
                    with self.tracer.provider.in_subsegment(
                        f"db_{operation}"
                    ) as subsegment:
                        subsegment.put_annotation("table", table)
                        subsegment.put_annotation("operation", operation)
                        return func(*args, **kwargs)
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def trace_external_call(self, service: str, operation: str):
        """Trace external service calls."""
        if not self.tracer:
            return lambda func: func

        def decorator(func):
            def wrapper(*args, **kwargs):
                if self.tracer and self.tracer.provider:
                    with self.tracer.provider.in_subsegment(
                        f"{service}_{operation}"
                    ) as subsegment:
                        subsegment.put_annotation("service", service)
                        subsegment.put_annotation("operation", operation)
                        return func(*args, **kwargs)
                return func(*args, **kwargs)

            return wrapper

        return decorator


# Global tracer instance
tracer = PerformanceTracer()
