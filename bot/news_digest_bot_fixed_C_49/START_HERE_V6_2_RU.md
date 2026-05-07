# Как запускать v6.2

1. Распакуй архив поверх отдельной папки проекта.
2. Проверь `.env`:

```env
APP_DEBUG=true
OPENROUTER_DEBUG_REJECTIONS=true
OPENROUTER_ALLOW_SEARCH_SNIPPET_FALLBACK=true
OPENROUTER_MAX_WEAK_FRESHNESS_ITEMS_PER_DIGEST=1
```

3. Запусти через Docker:

```cmd
docker compose up --build --force-recreate
```

Или с логом:

```cmd
powershell -Command "docker compose up --build --force-recreate 2>&1 | Tee-Object -FilePath debug_v6_2.log"
```

4. Тестовые классы тем:

```text
sports_team: Real Madrid, Arsenal, Bayern Munich
brand_company: Lexus, Audi, Dyson, Microsoft
entertainment_company: Universal Pictures, Disney, Netflix
person: Leonardo DiCaprio, Pavel Durov
city: Kyiv, Lviv, Paris
crypto: bitcoin, Ethereum
ambiguous_acronym: CS, AI, X
```

5. После теста вытащи диагностику:

```cmd
findstr /I "source_fetch_plan source_fetch_pass source_fetch_success source_fetch_empty candidate_decision candidate_rejected publish_done skipped topic_kind reason" debug_v6_2.log > search_debug_v6_2_only.txt
```

