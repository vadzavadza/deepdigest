# v6.3 Evaluation & Replay Framework

Эта версия не пытается «ещё раз угадать» правильные фильтры по скриншотам. Она добавляет измерительный слой, чтобы дальше улучшать новостной поиск быстрее и дешевле.

## Что добавлено

1. **Search run dumps**
   Каждый live-запуск может сохранять JSON-файл со всей поисковой диагностикой:
   - тема;
   - определённый `topic_kind`;
   - query variants;
   - raw candidates от OpenRouter;
   - решения по кандидатам (`candidate_decision`);
   - финальные выбранные материалы;
   - причины отказов.

2. **Replay report**
   Сохранённые JSON-файлы можно анализировать локально без новых OpenRouter-запросов:

   ```cmd
   docker compose run --rm app python -m app.tools.replay_search_run debug_runs/*.json --out debug_runs/replay_report.md
   ```

3. **Benchmark query-plan report**
   Можно отдельно проверить, как classifier/query-planner понимает эталонные темы, тоже без OpenRouter:

   ```cmd
   docker compose run --rm app python -m app.tools.benchmark_plan --input eval_fixtures/benchmark_topics.jsonl --out debug_runs/benchmark_plan_report.md
   ```

4. **Docker volumes**
   В `docker-compose.yml` добавлены volume-маунты:
   - `./debug_runs:/app/debug_runs`
   - `./eval_fixtures:/app/eval_fixtures`

   Поэтому JSON-дампы и отчёты будут лежать на Windows-хосте в папке проекта.

## Почему это важно

Раньше процесс был такой:

```text
скрин → догадка → патч → новый платный live-тест
```

Теперь процесс должен быть такой:

```text
live-тест → сохраняем raw candidates/decisions → replay/анализ бесплатно → точечный патч
```

Это должно сократить расход денег и убрать ощущение бега на месте.

## Новые настройки `.env`

```env
SEARCH_DEBUG_DUMP_ENABLED=true
SEARCH_DEBUG_DUMP_DIR=debug_runs
SEARCH_EVAL_FIXTURE_DIR=eval_fixtures
APP_DEBUG=true
OPENROUTER_DEBUG_REJECTIONS=true
```

Для обычной эксплуатации можно потом выключить:

```env
SEARCH_DEBUG_DUMP_ENABLED=false
```

## Что смотреть в `replay_report.md`

- `provider_returned_zero` — OpenRouter реально дал 0.
- `filter_or_selection_zeroed_results` — OpenRouter дал кандидатов, но наш фильтр/selection всё убил.
- `only_weak_freshness_selected` — отправлены только материалы без подтверждённой даты.
- `review_or_buying_guide_candidates_present` — в выдаче были reviews/guides.
- `hub_pages_present_in_candidates` — OpenRouter принёс страницы-разделы/хабы.

## Важно

Это не финальная «качество v6.3». Это инструмент, чтобы правильно довести качество. Следующий quality patch надо делать уже по replay-отчётам, а не по единичным скриншотам.
