from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ConnectorStats:
    name: str
    calls: int = 0
    errors: int = 0
    last_status: Optional[int] = None
    last_error: Optional[str] = None
    total_latency_ms: int = 0
    last_latency_ms: Optional[int] = None

    def as_dict(self) -> Dict:
        avg = (self.total_latency_ms / self.calls) if self.calls else 0
        return {
            "name": self.name,
            "calls": self.calls,
            "errors": self.errors,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "avg_latency_ms": int(avg),
            "last_latency_ms": self.last_latency_ms,
        }


class InstrumentationService:
    """Process-local counters for connector usage/errors/latency."""

    def __init__(self) -> None:
        self._stats: Dict[str, ConnectorStats] = {}

    def record(self, name: str, *, ok: bool, status: Optional[int], latency_ms: int, error: Optional[str] = None) -> None:
        st = self._stats.setdefault(name, ConnectorStats(name=name))
        st.calls += 1
        st.total_latency_ms += latency_ms
        st.last_latency_ms = latency_ms
        st.last_status = status
        if not ok:
            st.errors += 1
            st.last_error = error or st.last_error

    def get(self, name: str) -> Dict:
        return self._stats.get(name, ConnectorStats(name=name)).as_dict()

    def all(self) -> Dict[str, Dict]:
        return {k: v.as_dict() for k, v in self._stats.items()}

