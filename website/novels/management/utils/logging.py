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


class TimingMixin:
    """Mixin for management commands with timing support."""

    def start_timer(self, name):
        """Start a named timer."""
        if not hasattr(self, "_timers"):
            self._timers = {}
        self._timers[name] = time.perf_counter()

    def stop_timer(self, name):
        """Stop a named timer and return elapsed time."""
        if not hasattr(self, "_timers") or name not in self._timers:
            return 0.0
        elapsed = time.perf_counter() - self._timers.pop(name)
        return elapsed

    def log_step(self, name, func, *args, **kwargs):
        """Execute function with timing and logging."""
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        self.stdout.write(f"    {name}: {elapsed:.2f}s")
        return result
