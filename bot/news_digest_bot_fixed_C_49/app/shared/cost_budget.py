from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class BudgetExhausted(RuntimeError):
    """Raised when a topic run is too close to the configured hard cost cap."""


@dataclass(slots=True)
class BudgetEvent:
    label: str
    estimated_cost_usd: float
    charged_cost_usd: float
    usage_cost_usd: float | None = None
    generation_id: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "estimated_cost_usd": round(self.estimated_cost_usd, 8),
            "charged_cost_usd": round(self.charged_cost_usd, 8),
            "usage_cost_usd": None if self.usage_cost_usd is None else round(self.usage_cost_usd, 8),
            "generation_id": self.generation_id,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class CostBudget:
    """Best-effort per-topic run budget ledger.

    OpenRouter returns precise usage/cost in successful responses. Before a call is made, however,
    the application can only enforce the cap using conservative estimates. This class therefore:
    - blocks new calls that would exceed the hard cap by estimate;
    - records actual OpenRouter usage.cost when it is present;
    - falls back to the estimate when usage.cost is missing.
    """

    hard_limit_usd: float
    soft_limit_usd: float
    stop_margin_usd: float = 0.0
    spent_usd: float = 0.0
    events: list[BudgetEvent] = field(default_factory=list)
    blocked_events: list[dict[str, Any]] = field(default_factory=list)

    def can_spend(self, estimated_cost_usd: float, *, reserve_after_usd: float = 0.0) -> bool:
        estimated = max(float(estimated_cost_usd), 0.0)
        reserve_after = max(float(reserve_after_usd), 0.0)
        effective_cap = max(self.hard_limit_usd - max(self.stop_margin_usd, 0.0), 0.0)
        return self.spent_usd + estimated + reserve_after <= effective_cap + 1e-12

    def require_spend(self, label: str, estimated_cost_usd: float, *, reserve_after_usd: float = 0.0) -> None:
        if self.can_spend(estimated_cost_usd, reserve_after_usd=reserve_after_usd):
            return
        self.blocked_events.append(
            {
                "label": label,
                "estimated_cost_usd": round(max(float(estimated_cost_usd), 0.0), 8),
                "reserve_after_usd": round(max(float(reserve_after_usd), 0.0), 8),
                "spent_usd": round(self.spent_usd, 8),
                "hard_limit_usd": round(self.hard_limit_usd, 8),
                "stop_margin_usd": round(max(self.stop_margin_usd, 0.0), 8),
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        raise BudgetExhausted(
            f"Budget exhausted before {label}: spent={self.spent_usd:.6f}, "
            f"estimate={estimated_cost_usd:.6f}, cap={self.hard_limit_usd:.6f}"
        )

    def record_call(
        self,
        *,
        label: str,
        estimated_cost_usd: float,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BudgetEvent:
        usage = (payload or {}).get("usage") if isinstance(payload, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        usage_cost = _float_or_none(usage.get("cost"))
        charged = usage_cost if usage_cost is not None else max(float(estimated_cost_usd), 0.0)
        event = BudgetEvent(
            label=label,
            estimated_cost_usd=max(float(estimated_cost_usd), 0.0),
            charged_cost_usd=max(float(charged), 0.0),
            usage_cost_usd=usage_cost,
            generation_id=str((payload or {}).get("id") or "") or None,
            prompt_tokens=_int_or_none(usage.get("prompt_tokens")),
            completion_tokens=_int_or_none(usage.get("completion_tokens")),
            total_tokens=_int_or_none(usage.get("total_tokens")),
            metadata=metadata or {},
        )
        self.spent_usd += event.charged_cost_usd
        self.events.append(event)
        return event

    @property
    def remaining_usd(self) -> float:
        return max(self.hard_limit_usd - self.spent_usd, 0.0)

    @property
    def soft_remaining_usd(self) -> float:
        return max(self.soft_limit_usd - self.spent_usd, 0.0)

    @property
    def is_over_soft_limit(self) -> bool:
        return self.spent_usd >= self.soft_limit_usd

    def as_counters(self) -> dict[str, Any]:
        return {
            "budget_hard_limit_usd": round(self.hard_limit_usd, 8),
            "budget_soft_limit_usd": round(self.soft_limit_usd, 8),
            "budget_stop_margin_usd": round(self.stop_margin_usd, 8),
            "budget_spent_usd": round(self.spent_usd, 8),
            "budget_remaining_usd": round(self.remaining_usd, 8),
            "budget_over_soft_limit": self.is_over_soft_limit,
            "budget_calls": len(self.events),
            "budget_blocked_calls": len(self.blocked_events),
            "budget_events": [event.as_dict() for event in self.events],
            "budget_blocked_events": self.blocked_events,
        }


def _float_or_none(value: Any) -> float | None:
    if value in (None, "", False):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _int_or_none(value: Any) -> int | None:
    if value in (None, "", False):
        return None
    try:
        return int(value)
    except Exception:
        return None
