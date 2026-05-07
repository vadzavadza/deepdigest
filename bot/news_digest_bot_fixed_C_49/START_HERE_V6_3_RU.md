# START HERE — v6.3 Eval/Replay

## 1. Обнови `.env`

Добавь или проверь:

```env
APP_DEBUG=true
OPENROUTER_DEBUG_REJECTIONS=true
SEARCH_DEBUG_DUMP_ENABLED=true
SEARCH_DEBUG_DUMP_DIR=debug_runs
SEARCH_EVAL_FIXTURE_DIR=eval_fixtures
```

## 2. Запусти Docker

```cmd
powershell -Command "docker compose up --build --force-recreate 2>&1 | Tee-Object -FilePath debug_v6_3.log"
```

## 3. Прогони не больше 8–12 тем

Например:

```text
Real Madrid
CS
Lexus
Audi
Universal Pictures
Leonardo DiCaprio
bitcoin
Kyiv
```

## 4. Сгенерируй replay report

В новом CMD из папки проекта:

```cmd
docker compose run --rm app python -m app.tools.replay_search_run debug_runs/*.json --out debug_runs/replay_report.md --json-out debug_runs/replay_summary.json
```

## 5. Сгенерируй benchmark plan report

```cmd
docker compose run --rm app python -m app.tools.benchmark_plan --input eval_fixtures/benchmark_topics.jsonl --out debug_runs/benchmark_plan_report.md --json-out debug_runs/benchmark_plan_report.json
```

## 6. Что прислать в чат

Пришли эти файлы:

```text
debug_runs/replay_report.md
debug_runs/benchmark_plan_report.md
```

Если хочешь, можешь ещё прислать 3–5 скринов Telegram, но главное теперь — отчёты.

## Безопасность

В `debug_v6_3.log` может попадать Telegram token через HTTP debug. Не отправляй полный лог, лучше отправляй только replay/benchmark reports. Если токен уже светился, перевыпусти его через BotFather.
