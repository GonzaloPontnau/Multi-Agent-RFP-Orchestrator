"""Utilidades de cache en memoria con TTL y eviction LRU."""

import time
from collections import OrderedDict
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Cache simple en memoria con expiracion por TTL y eviction LRU."""

    def __init__(self, ttl_seconds: int, max_size: int):
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        self._store: OrderedDict[str, tuple[float, T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        """Obtiene un valor si existe y no expiro."""
        entry = self._store.get(key)
        if entry is None:
            return None

        ts, value = entry
        if time.time() - ts > self._ttl_seconds:
            self._store.pop(key, None)
            return None

        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: T) -> None:
        """Guarda un valor y aplica politica de eviction LRU."""
        self._store[key] = (time.time(), value)
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def clear(self) -> None:
        """Limpia todo el cache."""
        self._store.clear()
