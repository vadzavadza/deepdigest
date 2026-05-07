# Как запускать v6.1

1. Распакуй архив.
2. Проверь `.env`:

```env
APP_DEBUG=true
OPENROUTER_DEBUG_REJECTIONS=true
OPENROUTER_ALLOW_SEARCH_SNIPPET_FALLBACK=true
OPENROUTER_MAX_WEAK_FRESHNESS_ITEMS_PER_DIGEST=1
```

3. Запусти через Docker с логами:

```cmd
powershell -Command "docker compose up --build --force-recreate 2>&1 | Tee-Object -FilePath debug_v6_1.log"
```

4. Протестируй 5–7 разных тем.
5. Сохрани фильтрованный лог:

```cmd
findstr /I "source_fetch_plan source_fetch_pass source_fetch_success source_fetch_empty candidate_decision candidate_skipped story_skipped publish_done" debug_v6_1.log > search_debug_v6_1_only.txt
```

Не присылай `.env` целиком. В прошлых логах был Telegram token — лучше перевыпустить токен через BotFather.
