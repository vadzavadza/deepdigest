# START HERE — v5.3

## 1. Обнови `.env`

Если у тебя уже есть старый `.env`, новые значения из `.env.example` сами не подтянутся. Проверь вручную:

```env
OPENROUTER_WEB_SEARCH_MAX_RESULTS=15
OPENROUTER_TOPIC_BUDGET_USD=0.07
OPENROUTER_SEARCH_RESULT_COST_USD=0.004
OPENROUTER_WEB_SEARCH_RESULTS_PER_CALL=5
OPENROUTER_WEB_SEARCH_MAX_CALLS_PER_TOPIC=3
OPENROUTER_MIN_QUALITY_CANDIDATES=3
OPENROUTER_ALLOW_PLUGIN_FALLBACK=false
OPENROUTER_DEBUG_REJECTIONS=true
OPENROUTER_MAX_ARTICLE_AGE_HOURS=168
OPENROUTER_REQUIRE_VERIFIED_PUBLISH_DATE=true
OPENROUTER_ALLOW_WEAK_PUBLISH_DATES=false
OPENROUTER_ALLOW_UNDATED_FALLBACK=false
OPENROUTER_FUTURE_SKEW_HOURS=12
OPENROUTER_ALLOW_SEARCH_SNIPPET_FALLBACK=true
OPENROUTER_SEARCH_SNIPPET_FALLBACK_MIN_DIRECTNESS=12
OPENROUTER_SEARCH_SNIPPET_FALLBACK_MIN_CONFIDENCE=2
OPENROUTER_MAX_WEAK_FRESHNESS_ITEMS_PER_DIGEST=2
OPENROUTER_ADAPTIVE_TARGET_CANDIDATES=3
OPENROUTER_MIN_SEARCH_PASSES=2
IMMEDIATE_REPEAT_GUARD_MINUTES=15
```

## 2. Запусти тесты

```bash
pytest -q
```

## 3. Как тестировать руками

Проверяй не только “нашёл / не нашёл”, а поведение:

```text
- первый запуск темы;
- повторный запуск через 1 минуту;
- повторный запуск через 15+ минут;
- свежесть статей;
- не повторяется ли один и тот же сюжет;
- не пролезают ли category/news hub pages.
```

## 4. Что прислать, если результат странный

Лучше всего прислать:

```text
- тему;
- первый результат;
- второй результат;
- время между запусками;
- строки логов source_fetch_plan / source_fetch_pass / candidate_rejected / source_fetch_success.
```

Особенно важны новые логи `source_fetch_pass`: по ним будет видно, где именно теряются кандидаты.
