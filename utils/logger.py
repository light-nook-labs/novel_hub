"""Logging utilities for utils module.

Public API:
    get_logger(name) — get module-level logger
    log_time(func) — decorator: log function call + execution time
    timed(name=None) — context manager: log block execution time
    progress(iterable, desc, total) — tqdm wrapper, auto-enable if >30s
"""

import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator

from tqdm import tqdm

# Threshold for enabling tqdm (seconds)
TQDM_THRESHOLD = 30

# Default logging format
LOG_FORMAT = "[%(asctime)s] %(name)s %(levelname)s: %(message)s"
LOG_DATE = "%H:%M:%S"

# Configure root logger for utils
logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE, level=logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a module-level logger.

    Args:
        name: Logger name, typically __name__.

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


def log_time(func: Callable = None, *, logger: logging.Logger = None) -> Callable:
    """Decorator: log function call and execution time.

    Args:
        func: Function to decorate.
        logger: Logger to use (default: func's module logger).

    Returns:
        Decorated function.
    """

    def decorator(fn: Callable) -> Callable:
        _logger = logger or logging.getLogger(fn.__module__)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> Any:
            _logger.info("Starting %s", fn.__name__)
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                elapsed = time.perf_counter() - start
                _logger.info("Finished %s in %.2fs", fn.__name__, elapsed)
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                _logger.error("Failed %s after %.2fs: %s", fn.__name__, elapsed, e)
                raise

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


@contextmanager
def timed(name: str = None, logger: logging.Logger = None) -> Generator:
    """Context manager: log block execution time.

    Args:
        name: Block name for logging.
        logger: Logger to use.

    Usage:
        with timed("Loading data"):
            df = load_jsonl(path)
    """
    _logger = logger or logging.getLogger(__name__)
    _name = name or "block"
    _logger.info("Starting %s", _name)
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        _logger.info("Finished %s in %.2fs", _name, elapsed)


def progress(
    iterable=None,
    desc: str = None,
    total: int = None,
    logger: logging.Logger = None,
    **tqdm_kwargs,
) -> Any:
    """tqdm wrapper: auto-enable progress bar for long operations.

    Progress bar shows immediately; logging reports completion time.

    Args:
        iterable: Iterable to wrap.
        total: Total items (if not len(iterable)).
        desc: Description for progress bar.
        logger: Logger for completion message.

    Returns:
        tqdm-wrapped iterable.
    """
    _logger = logger or logging.getLogger(__name__)
    _desc = desc or "Processing"

    start = time.perf_counter()

    # Always show tqdm (caller decides when to use)
    bar = tqdm(iterable, desc=_desc, total=total, **tqdm_kwargs)

    # Wrap close to log time
    original_close = bar.close

    def close_with_log():
        original_close()
        elapsed = time.perf_counter() - start
        _logger.info("%s completed in %.2fs", _desc, elapsed)

    bar.close = close_with_log
    return bar


def should_use_tqdm(iterable, threshold: int = TQDM_THRESHOLD) -> bool:
    """Check if tqdm should be used based on estimated time.

    Args:
        iterable: Iterable to check.
        threshold: Time threshold in seconds.

    Returns:
        True if tqdm should be used.
    """
    # For large datasets, always use tqdm
    if hasattr(iterable, "__len__"):
        return len(iterable) > 1000
    return True
