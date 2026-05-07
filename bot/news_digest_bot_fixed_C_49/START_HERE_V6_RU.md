# START HERE — v6 Universal Search Core

1. Распакуй архив.
2. Перенеси свой `.env` или обнови существующий `.env`.
3. Добавь новые настройки:

```env
OPENROUTER_VERIFIED_HARD_MAX_ARTICLE_AGE_HOURS=720
OPENROUTER_FOLLOWUP_HARD_MAX_ARTICLE_AGE_HOURS=72
OPENROUTER_MAX_WEAK_FRESHNESS_ITEMS_PER_DIGEST=2
OPENROUTER_ALLOW_SEARCH_SNIPPET_FALLBACK=true
OPENROUTER_DEBUG_REJECTIONS=true
APP_DEBUG=true
```

4. Запуск через Docker:

```cmd
docker compose up --build --force-recreate
```

5. Для сбора логов в файл:

```cmd
docker compose up --build --force-recreate > debug.log 2>&1
```

6. В твоём compose сервис называется `app`, не `bot`. Проверка настроек:

```cmd
docker compose run --rm app python -c "from app.shared.settings import get_settings; s=get_settings(); print('model=',s.openrouter_search_model or s.openrouter_default_model); print('max_results=',s.openrouter_web_search_max_results); print('per_call=',s.openrouter_web_search_results_per_call); print('max_calls=',s.openrouter_web_search_max_calls_per_topic); print('budget=',s.openrouter_topic_budget_usd); print('soft_age=',s.openrouter_max_article_age_hours); print('hard_age=',s.openrouter_verified_hard_max_article_age_hours); print('weak_fallback=',s.openrouter_allow_search_snippet_fallback)"
```

7. Фильтр важных строк из логов:

```cmd
findstr /I "source_fetch_plan source_fetch_pass source_fetch_empty source_fetch_success candidate_decision candidate_rejected" debug.log > search_debug_only.txt
```

Важно: не присылай `.env` целиком и не присылай лог с токеном бота. Если токен уже попал в лог, перевыпусти его через BotFather.
