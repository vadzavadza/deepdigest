# Как запускать v5.4

1. Распакуй архив.
2. Проверь `.env`. Новых обязательных переменных в v5.4 нет, но значения из v5.3 должны остаться:

```env
OPENROUTER_WEB_SEARCH_MAX_RESULTS=15
OPENROUTER_WEB_SEARCH_RESULTS_PER_CALL=5
OPENROUTER_WEB_SEARCH_MAX_CALLS_PER_TOPIC=3
OPENROUTER_TOPIC_BUDGET_USD=0.07
OPENROUTER_ALLOW_SEARCH_SNIPPET_FALLBACK=true
OPENROUTER_MAX_WEAK_FRESHNESS_ITEMS_PER_DIGEST=2
OPENROUTER_REQUIRE_VERIFIED_PUBLISH_DATE=true
OPENROUTER_ALLOW_UNDATED_FALLBACK=false
OPENROUTER_DEBUG_REJECTIONS=true
IMMEDIATE_REPEAT_GUARD_MINUTES=15
```

3. Желательно прогнать:

```bash
pytest -q tests/test_quality_engine_v54.py tests/test_quality_engine_v53.py tests/test_freshness_guard_v51.py tests/test_quality_engine_v52.py
```

4. Затем тестируй живые темы парами: латиница / кириллица.
