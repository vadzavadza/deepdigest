# V7 Budget-Locked News Engine — старт

Это не очередной маленький фикс. V7 усиливает локальный редакционный мотор поверх OpenRouter:

- soft budget: `$0.07`
- hard cap: `$0.10`
- обычный режим: 2 search-pass по 5 результатов
- rescue mode: 3-й pass только если первые два дали мало качественных кандидатов
- OpenRouter остаётся источником кандидатов, локальный движок решает, что достойно отправки

## .env

Добавь или проверь:

```env
NEWS_TOPIC_SOFT_BUDGET_USD=0.07
NEWS_TOPIC_HARD_BUDGET_USD=0.10
OPENROUTER_RESERVED_LLM_BUDGET_USD=0.025
OPENROUTER_WEB_SEARCH_RESULTS_PER_CALL=5
OPENROUTER_WEB_SEARCH_MAX_CALLS_PER_TOPIC=3
OPENROUTER_WEB_SEARCH_NORMAL_MAX_CALLS=2
OPENROUTER_WEB_SEARCH_RESCUE_MAX_CALLS=3
OPENROUTER_MAX_WEAK_FRESHNESS_ITEMS_PER_DIGEST=1
APP_DEBUG=true
OPENROUTER_DEBUG_REJECTIONS=true
SEARCH_DEBUG_DUMP_ENABLED=true
SEARCH_DEBUG_DUMP_DIR=debug_runs
```

## Запуск

```cmd
powershell -Command "docker compose up --build --force-recreate 2>&1 | Tee-Object -FilePath debug_v7.log"
```

## После тестов

```cmd
docker compose run --rm app python -m app.tools.replay_search_run debug_runs/*.json --out debug_runs/replay_report_v7.md --json-out debug_runs/replay_summary_v7.json
```

Скидывай не полный `debug_v7.log`, а:

- `debug_runs/replay_report_v7.md`
- `debug_runs/replay_summary_v7.json`
- zip с `debug_runs/*.json`, если нужно разобрать кандидатов

## Важно

Если Telegram token попадал в логи, перевыпусти его через BotFather.
