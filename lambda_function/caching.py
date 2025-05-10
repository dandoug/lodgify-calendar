"""
Caching support used to hold Lodgify API results in-memory
"""
from typing import Any

from cachetools import TTLCache, Cache


class ResultsCache(TTLCache):
    """
    Cache for saving results of calling Lodgify APIs in-memory
    """
    def __setitem__(self, key, value: tuple[Any, Any, Any], cache_setitem=Cache.__setitem__):
        # Value is a tuple of (availability, rates, error)
        # Only add to cache if error is None
        if value[2] is None:
            super().__setitem__(key, value, cache_setitem=cache_setitem)


def cache_key(property_id, room_type_id, start_date, end_date, origin):
    """
    Don't include origin in the cache key, it is not relevant to what is cached
    """
    return f"{property_id}_{room_type_id}_{start_date}_{end_date}"
