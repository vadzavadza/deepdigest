# Test report v5.4

Проверено в этой среде:

```text
python -m py_compile app/search_v2/strategy.py app/search_v2/article_filter.py app/infrastructure/sources/openrouter_web_search.py tests/test_quality_engine_v54.py: PASS
manual deterministic v5.4 tests: PASS
zip integrity: PASS после сборки архива
```

Новый deterministic-тест без живого OpenRouter проверяет:

- `paris` и `Париж` имеют общий canonical topic;
- `дайсан` нормализуется в `dyson`;
- `Trump`/`Трамп` и `Pavel Durov`/`Павел Дуров` классифицируются как `person`;
- provider freshness hint больше не использует жёсткий `published after YYYY-MM-DD`;
- кириллическое совпадение темы считается direct evidence, а не `indirect_relevance`.

Живой OpenRouter/Telegram здесь не прогонялся: нет твоих ключей и runtime-окружения.
