import asyncio
import time
from typing import Any, Dict, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int, max_entries: int = 500):
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._store: Dict[Any, Any] = {}
        self._timestamps: Dict[Any, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: Any) -> Optional[Any]:
        async with self._lock:
            timestamp = self._timestamps.get(key)
            if timestamp is None:
                return None
            if time.time() - timestamp > self._ttl_seconds:
                self._store.pop(key, None)
                self._timestamps.pop(key, None)
                return None
            return self._store.get(key)

    async def set(self, key: Any, value: Any) -> None:
        async with self._lock:
            if len(self._store) >= self._max_entries and key not in self._store:
                oldest = min(self._timestamps.items(), key=lambda item: item[1])[0]
                self._store.pop(oldest, None)
                self._timestamps.pop(oldest, None)
            self._store[key] = value
            self._timestamps[key] = time.time()

    async def delete(self, key: Any) -> None:
        async with self._lock:
            self._store.pop(key, None)
            self._timestamps.pop(key, None)
