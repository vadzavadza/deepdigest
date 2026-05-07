# Test Report v5.1

Команды, выполненные в контейнере:

```bash
python -m compileall -q app tests
pytest -q
```

Результат:

```text
29 passed in 4.32s
```

Живой Telegram/OpenRouter не запускался в контейнере, потому что здесь нет твоих реальных ключей и окружения.
