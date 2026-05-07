# v7.1 OpenRouter-Native News Agent — старт

Эта версия не переписывает весь бот. Она меняет то, как используется OpenRouter:

- OpenRouter теперь получает задачу не просто “дай ссылки”, а “найди и оцени конкретные новостные статьи”.
- Запрос просит строгий JSON: title, url, source, published_at, summary, topic_match, source_quality, reject_reason.
- Локальный движок остаётся safety net: проверяет URL, свежесть, source quality, повторы, weak freshness и бюджет.

## Важные `.env`

```env
NEWS_TOPIC_SOFT_BUDGET_USD=0.07
NEWS_TOPIC_HARD_BUDGET_USD=0.10
OPENROUTER_WEB_SEARCH_RESULTS_PER_CALL=5
OPENROUTER_WEB_SEARCH_NORMAL_MAX_CALLS=2
OPENROUTER_WEB_SEARCH_RESCUE_MAX_CALLS=3
OPENROUTER_NATIVE_NEWS_AGENT_ENABLED=true
OPENROUTER_NATIVE_JUDGE_MIN_TOPIC_MATCH=0.62
OPENROUTER_NATIVE_JUDGE_MAX_CANDIDATES=8
OPENROUTER_NATIVE_REJECT_WEAK_SOURCES=true
APP_DEBUG=true
OPENROUTER_DEBUG_REJECTIONS=true
SEARCH_DEBUG_DUMP_ENABLED=true
SEARCH_DEBUG_DUMP_DIR=debug_runs
```

## Запуск

```cmd
powershell -Command "docker compose up --build --force-recreate 2>&1 | Tee-Object -FilePath debug_v7_1.log"
```

## После теста

```cmd
docker compose run --rm app python -m app.tools.replay_search_run debug_runs/*.json --out debug_runs/replay_report_v7_1.md --json-out debug_runs/replay_summary_v7_1.json
```

Скидывать лучше:

- `debug_runs/replay_report_v7_1.md`
- `debug_runs/replay_summary_v7_1.json`
- скрины Telegram

Полный `debug_v7_1.log` лучше не скидывать: даже с фильтрами он может содержать лишнее.
