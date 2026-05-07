# START HERE v7.2

Этот архив — v7.1 + cost guard patch.

## Главное изменение

Один запуск темы теперь имеет общий budget ledger для:

- OpenRouter web search;
- relevance checks;
- summaries;
- translations.

Раньше hard cap в основном ограничивал search passes. Теперь дополнительные LLM-вызовы тоже проходят через тот же guard.

## Рекомендуемые настройки для потолка около 10 центов

```env
NEWS_TOPIC_SOFT_BUDGET_USD=0.07
NEWS_TOPIC_HARD_BUDGET_USD=0.10
NEWS_TOPIC_STOP_MARGIN_USD=0.005
OPENROUTER_WEB_SEARCH_RESULTS_PER_CALL=5
OPENROUTER_WEB_SEARCH_MAX_CALLS_PER_TOPIC=3
OPENROUTER_WEB_SEARCH_NORMAL_MAX_CALLS=2
OPENROUTER_WEB_SEARCH_RESCUE_MAX_CALLS=3
OPENROUTER_RESERVED_LLM_BUDGET_USD=0.025
OPENROUTER_SEARCH_RESULT_COST_USD=0.004
OPENROUTER_SEARCH_CALL_MODEL_RESERVE_USD=0.002
OPENROUTER_LLM_RELEVANCE_ESTIMATED_COST_USD=0.002
OPENROUTER_LLM_SUMMARY_ESTIMATED_COST_USD=0.003
OPENROUTER_LLM_TRANSLATION_ESTIMATED_COST_USD=0.002
LLM_SKIP_RELEVANCE_FOR_NATIVE_JUDGED_CANDIDATES=true
LLM_NATIVE_RELEVANCE_MIN_TOPIC_MATCH=0.70
```

## Где смотреть расходы

После каждого запуска смотри `job_runs.counters`:

- `budget_spent_usd`
- `budget_remaining_usd`
- `budget_over_soft_limit`
- `budget_events`
- `budget_blocked_events`
- `relevance_checks`
- `relevance_skipped_native`

Manual internal endpoint также возвращает краткую budget-сводку.

## Проверка

Минимальная проверка синтаксиса:

```bash
python -m compileall -q app tests
```

Unit test по ledger:

```bash
pytest -q tests/test_cost_budget_v72.py
```
