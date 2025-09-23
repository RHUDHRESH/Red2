from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .instrumentation_service import InstrumentationService


@dataclass
class ConnectorInfo:
    name: str
    enabled: bool = True
    notes: str = ""


class ConnectorManager:
    """Manages connector enable/disable state and basic metadata.

    Real tokens live in OAuthService; this class only tracks toggles and feeds instrumentation.
    """

    def __init__(self, metrics: InstrumentationService) -> None:
        self._metrics = metrics
        self._connectors: Dict[str, ConnectorInfo] = {}

    def register(self, name: str, notes: str = "") -> None:
        self._connectors.setdefault(name, ConnectorInfo(name=name, notes=notes))

    def enable(self, name: str) -> None:
        self._connectors.setdefault(name, ConnectorInfo(name=name)).enabled = True

    def disable(self, name: str) -> None:
        self._connectors.setdefault(name, ConnectorInfo(name=name)).enabled = False

    def is_enabled(self, name: str) -> bool:
        info = self._connectors.get(name)
        return bool(info and info.enabled)

    def list(self) -> Dict[str, Dict]:
        return {k: {"enabled": v.enabled, "notes": v.notes, **self._metrics.get(k)} for k, v in self._connectors.items()}

