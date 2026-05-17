import time
from typing import Any, Callable, Dict, Optional, Tuple


class TTLCache:
    def __init__(self, default_ttl: int = 3600) -> None:
        self._store: Dict[str, Tuple[float, Any]] = {}
        self.default_ttl = default_ttl

    def _key(self, *args: Any, **kwargs: Any) -> str:
        parts = [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
        return ":".join(parts)

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires, value = entry
        if time.monotonic() > expires:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires = time.monotonic() + (ttl if ttl is not None else self.default_ttl)
        self._store[key] = (expires, value)

    def clear(self) -> None:
        self._store.clear()

    def memoize(
        self, fn: Callable, ttl: Optional[int] = None
    ) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = self._key(*args, **kwargs)
            cached = self.get(key)
            if cached is not None:
                return cached
            result = fn(*args, **kwargs)
            self.set(key, result, ttl=ttl)
            return result
        return wrapper


gee_cache = TTLCache(default_ttl=3600)
c3s_cache = TTLCache(default_ttl=21600)
