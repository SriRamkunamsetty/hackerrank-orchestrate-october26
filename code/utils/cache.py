"""
Thread-safe caching utility for evidence loading and LLM evaluations.
"""
import functools
from typing import Any, Callable

def memoize(func: Callable) -> Callable:
    """Simple in-memory memoization decorator."""
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, frozenset(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    wrapper.clear_cache = cache.clear
    return wrapper
