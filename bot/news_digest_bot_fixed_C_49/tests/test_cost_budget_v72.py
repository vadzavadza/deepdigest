from __future__ import annotations

import pytest

from app.shared.cost_budget import BudgetExhausted, CostBudget


def test_budget_uses_stop_margin_for_preflight() -> None:
    budget = CostBudget(hard_limit_usd=0.10, soft_limit_usd=0.07, stop_margin_usd=0.005)

    assert budget.can_spend(0.095)
    assert not budget.can_spend(0.096)

    with pytest.raises(BudgetExhausted):
        budget.require_spend("too_expensive", 0.096)

    assert budget.blocked_events


def test_budget_records_actual_usage_cost_when_available() -> None:
    budget = CostBudget(hard_limit_usd=0.10, soft_limit_usd=0.07)

    budget.record_call(
        label="openrouter.llm.SummaryResult",
        estimated_cost_usd=0.003,
        payload={
            "id": "gen_123",
            "usage": {
                "cost": 0.0015,
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        },
    )

    assert budget.spent_usd == 0.0015
    counters = budget.as_counters()
    assert counters["budget_events"][0]["usage_cost_usd"] == 0.0015
    assert counters["budget_events"][0]["generation_id"] == "gen_123"


def test_budget_falls_back_to_estimate_without_usage_cost() -> None:
    budget = CostBudget(hard_limit_usd=0.10, soft_limit_usd=0.07)

    budget.record_call(label="openrouter.web_search.native", estimated_cost_usd=0.022, payload={})

    assert budget.spent_usd == 0.022
