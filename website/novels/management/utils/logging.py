"""Logging utilities for management commands."""

import time
import functools


def log_timing(message=None):
    """Decorator to log function execution time to stdout."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            msg = message or func.__name__
            t0 = time.perf_counter()
            result = func(self, *args, **kwargs)
            elapsed = time.perf_counter() - t0
            self.stdout.write(f"    {msg}: {elapsed:.2f}s")
            return result

        return wrapper

    return decorator
