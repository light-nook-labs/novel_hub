import logging
import time
import functools

# Package level logger
logger = logging.getLogger(__name__)


def log_elapsed(func):
    """Universal decorator to record function execution time."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info("Function [%s] executed in %.4f seconds", func.__name__, elapsed)
        return result

    return wrapper


from .transform import *

__all__ = ["logger", "log_elapsed"]
