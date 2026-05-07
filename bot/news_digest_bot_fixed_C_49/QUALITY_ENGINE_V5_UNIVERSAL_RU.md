# Newsbot Quality Engine v5 Universal Patch

Это прозрачный patch поверх твоего исходного архива `improved_retrieval_core_team_diversity(2).zip`.

## Главная цель

Сделать универсальный новостной retrieval/ranking слой:

- не подгонять движок под несколько конкретных тестовых тем;
- искать качественные новости в пределах бюджета;
- не добивать дайджест мусором ради количества;
- логировать причины, почему кандидаты отброшены;
- сохранять source diversity в маленьком дайджесте.

## Что изменено

### 1. Universal topic strategy

`app/search_v2/strategy.py`

Добавлены/улучшены общие типы тем:

- `country`
- `city`
- `geo_region`
- `person`
- `business`
- `crypto`
- `sports`
- `esports`
- `entertainment`
- `team_org`
- `entity_symbol`
- `broad_single`
- `broad_dual`

Это не специальные хаки под конкретные запросы. Query angles строятся по типу темы.

### 2. Quality gates

`app/search_v2/article_filter.py`

Добавлены:

- `candidate_quality()`
- `directness_score()`
- rejection reasons:
  - `indirect_relevance`
  - `wrong_entity_context`
  - `section_or_index_page`
  - `evergreen_or_service_content`
  - `finance_only_drift`
  - `semantic_only_match`
  - `low_directness`
  - `low_article_confidence`

### 3. Budget controller

`app/infrastructure/sources/openrouter_web_search.py`

Добавлены настройки:

```env
OPENROUTER_WEB_SEARCH_MAX_RESULTS=16
OPENROUTER_TOPIC_BUDGET_USD=0.07
OPENROUTER_SEARCH_RESULT_COST_USD=0.004
OPENROUTER_WEB_SEARCH_RESULTS_PER_CALL=8
OPENROUTER_WEB_SEARCH_MAX_CALLS_PER_TOPIC=2
OPENROUTER_MIN_QUALITY_CANDIDATES=4
OPENROUTER_ALLOW_PLUGIN_FALLBACK=false
OPENROUTER_DEBUG_REJECTIONS=true
LLM_RELEVANCE_MAX_CHECKS_PER_TOPIC=8
```

По умолчанию retrieval budget рассчитан как:

```text
2 calls × 8 results × $0.004 = ~$0.064
```

Важно: это локальный guardrail для web-search result budget. Итоговая стоимость ещё зависит от модели/токенов для relevance, summary и translation.

### 4. Staged source diversity

`app/domain/policies/ranking.py`

Теперь выбор историй идёт в два прохода:

1. Сначала разные домены.
2. Повтор домена разрешается только если хороших альтернатив не хватает.

### 5. Soft incremental fallback

`app/application/services/topic_processing.py`

Если прошлый запуск был “тонким” и отправил мало новостей, следующий запуск не душит тему слишком узким окном.

Также `force=True` теперь реально расширяет окно до 7 дней.

### 6. Failure tracking

`job_run` теперь коммитится как `RUNNING` до тяжёлой обработки, чтобы при ошибке можно было записать `FAILED`.

## Прозрачность архива

Внутри архива лежат:

- `PATCH.diff`
- `MANIFEST_BEFORE.txt`
- `MANIFEST_AFTER.txt`
- `CHANGED_FILES.md`
- `REMOVED_FILES.md`
- `TEST_REPORT.md`

Рабочие файлы не удалены.

## Как запускать

```bash
unzip newsbot_v5_universal_patch_ready.zip
cd newsbot_v5_universal_patch_ready
cp .env.example .env
```

Если у тебя уже есть `.env`, вручную перенеси новые `OPENROUTER_*` настройки из `.env.example`.

Потом:

```bash
pytest -q tests/test_search_v2.py tests/test_disambiguation_diversity.py tests/test_quality_filters.py tests/test_quality_engine_v5.py
pytest -q
```
