# TEST REPORT v6.3

Проверено в sandbox:

- `py_compile` для новых файлов: PASS
- `py_compile` для изменённого OpenRouter source/settings/tools: PASS
- zip integrity: PASS

Полный live OpenRouter/Telegram test здесь не запускался, потому что нужны реальные ключи и Docker/Webhook окружение.

Локально после распаковки можно проверить:

```cmd
docker compose build

docker compose run --rm app python -m app.tools.benchmark_plan --input eval_fixtures/benchmark_topics.jsonl --out debug_runs/benchmark_plan_report.md
```
