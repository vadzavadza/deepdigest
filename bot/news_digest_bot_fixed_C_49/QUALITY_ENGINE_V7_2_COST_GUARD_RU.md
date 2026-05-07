# v7.2 — общий budget guard для одного запуска темы

Цель патча: один запуск темы не должен незаметно выходить за `NEWS_TOPIC_HARD_BUDGET_USD`, даже если после web search дополнительно вызываются relevance / summary / translation LLM-запросы.

## Что добавлено

- `app/shared/cost_budget.py` — общий per-run ledger расходов.
- Подключение ledger к `OpenRouterWebSearchSource` и `OpenRouterProvider`.
- Preflight-проверка перед каждым OpenRouter-вызовом.
- Учёт реального `usage.cost` из ответа OpenRouter, если поле есть.
- Fallback на оценочную стоимость, если `usage.cost` отсутствует.
- Запись budget counters в `job_runs.counters`.
- Возврат `budget_spent_usd`, `budget_remaining_usd`, `budget_over_soft_limit` из internal manual endpoint.

## Важные настройки

```env
NEWS_TOPIC_SOFT_BUDGET_USD=0.07
NEWS_TOPIC_HARD_BUDGET_USD=0.10
NEWS_TOPIC_STOP_MARGIN_USD=0.005
OPENROUTER_SEARCH_RESULT_COST_USD=0.004
OPENROUTER_SEARCH_CALL_MODEL_RESERVE_USD=0.002
OPENROUTER_LLM_RELEVANCE_ESTIMATED_COST_USD=0.002
OPENROUTER_LLM_SUMMARY_ESTIMATED_COST_USD=0.003
OPENROUTER_LLM_TRANSLATION_ESTIMATED_COST_USD=0.002
```

`NEWS_TOPIC_STOP_MARGIN_USD=0.005` значит, что новые вызовы перестают стартовать примерно после $0.095, чтобы оставить запас под округления и неожиданные provider-side отличия.

## Оптимизация качества/стоимости

В v7.1 OpenRouter native news agent уже возвращает structured judgement: `native_judge`, `native_topic_match`, `source_quality`, `is_news_article`. В v7.2 добавлен режим:

```env
LLM_SKIP_RELEVANCE_FOR_NATIVE_JUDGED_CANDIDATES=true
LLM_NATIVE_RELEVANCE_MIN_TOPIC_MATCH=0.70
```

Если кандидат уже прошёл native judge + локальные фильтры + directness gate, отдельный relevance LLM-call пропускается. Это сохраняет качество, но снижает стоимость на хороших кандидатах.

## Изменение pipeline

До v7.2 expensive relevance check мог происходить до части дешёвых проверок. Теперь порядок такой:

1. URL fingerprint уже отправлялся?
2. article/source quality отрицательные?
3. immediate repeat guard?
4. fuzzy title signature уже отправлялась?
5. native judge достаточно сильный? Если да — пропустить relevance LLM.
6. И только потом relevance LLM, если он ещё нужен.

## Ограничение

Hard cap — best-effort runtime guard. До старта запроса точная стоимость неизвестна, поэтому preflight использует консервативные оценки. После успешного ответа ledger заменяет оценку на реальный `usage.cost`, если OpenRouter его вернул.
