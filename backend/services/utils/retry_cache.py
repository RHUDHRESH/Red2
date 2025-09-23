from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple


def _now_ms() -> int:
    return int(time.time() * 1000)


class TTLCache:
    """Simple in-memory TTL cache (best-effort; process-local)."""

    def __init__(self, max_size: int = 512, ttl_s: float = 60.0) -> None:
        self._max = max_size
        self._ttl_ms = int(ttl_s * 1000)
        self._data: Dict[str, Tuple[int, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        it = self._data.get(key)
        if not it:
            return None
        ts, val = it
        if _now_ms() - ts > self._ttl_ms:
            self._data.pop(key, None)
            return None
        return val

    def set(self, key: str, value: Any) -> None:
        if len(self._data) >= self._max:
            # remove random key (cheap LRU-ish)
            self._data.pop(next(iter(self._data)), None)
        self._data[key] = (_now_ms(), value)


async def with_backoff(
    fn: Callable[[], Awaitable[Any]],
    *,
    retries: int = 4,
    base_delay_s: float = 0.5,
    max_delay_s: float = 8.0,
    retry_on: Tuple[int, ...] = (408, 409, 425, 429, 500, 502, 503, 504),
) -> Any:
    """Run fn() with exponential backoff + jitter.

    If fn raises or returns an httpx.Response-like object with .status_code in retry_on,
    we retry with backoff.
    """

    last_exc: Optional[Exception] = None
    delay = base_delay_s
    for attempt in range(retries + 1):
        try:
            res = await fn()
            sc = getattr(res, "status_code", None)
            if sc is not None and sc in retry_on:
                raise RuntimeError(f"retryable status {sc}")
            return res
        except Exception as e:
            last_exc = e
            if attempt >= retries:
                break
            jitter = random.uniform(0.5, 1.5)
            await asyncio.sleep(min(max_delay_s, delay * jitter))
            delay *= 2
    if last_exc:
        raise last_exc
    raise RuntimeError("with_backoff failed without exception")


@dataclass
class BatchItem:
    key: str
    value: Any


class BatchExecutor:
    """Aggregate small calls into batches via flush coroutine.

    Use enqueue(key, value) and flush() will be called when size >= batch_size or after flush_interval_s by caller.
    """

    def __init__(self, batch_size: int = 50):
        self._batch_size = batch_size
        self._items: list[BatchItem] = []

    def enqueue(self, key: str, value: Any) -> None:
        self._items.append(BatchItem(key, value))

    def should_flush(self) -> bool:
        return len(self._items) >= self._batch_size

    def drain(self) -> list[BatchItem]:
        out = self._items
        self._items = []
        return out

