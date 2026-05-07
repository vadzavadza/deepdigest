# TEST_REPORT_V6_2

Проверено в sandbox:

- `py_compile` для изменённых файлов: PASS
- deterministic checks для strategy/article_filter: PASS
- zip integrity после сборки: PASS

Полный живой тест OpenRouter/Telegram здесь не запускался, потому что нужны реальные ключи и окружение.

Рекомендуемые локальные тесты:

```cmd
pytest -q tests/test_quality_engine_v6.py tests/test_quality_engine_v61.py tests/test_quality_engine_v62.py tests/test_ranking.py tests/test_search_v2.py tests/test_quality_filters.py
```
