from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.infrastructure.sources.base import SourceAdapter


class SourceRegistry:
    def __init__(self, adapters: Iterable[SourceAdapter]) -> None:
        self._adapters = list(adapters)

    @property
    def adapters(self) -> list[SourceAdapter]:
        return list(self._adapters)

    def attach_budget(self, budget: Any | None) -> None:
        for adapter in self._adapters:
            attach = getattr(adapter, "attach_budget", None)
            if callable(attach):
                attach(budget)
