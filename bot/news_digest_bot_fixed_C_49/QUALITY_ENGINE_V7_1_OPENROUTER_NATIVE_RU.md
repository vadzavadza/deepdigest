# v7.1: OpenRouter-Native News Agent

## Зачем

В v7 OpenRouter использовался в основном как источник ссылок. Это давало результат, но часть качества приходилось угадывать локальными правилами. В v7.1 OpenRouter используется глубже: модель с `openrouter:web_search` должна не только найти страницы, но и вернуть структурированную оценку кандидатов.

## Что изменено

1. **Native JSON news-agent режим**
   - Запрос к OpenRouter просит JSON `candidates[]`.
   - Каждый кандидат содержит `is_news_article`, `topic_match`, `source_quality`, `published_at`, `reject_reason`.
   - Плохие кандидаты отбрасываются до HTTP-enrich.

2. **Локальный safety net сохранён**
   - Даже если OpenRouter считает статью хорошей, локальный движок всё равно проверяет article-likeness, source vertical, freshness, hub/review/support страницы и повторы.

3. **Строже финальный селектор**
   - Источники с отрицательным source weight больше не проходят в финальную отправку.
   - Weak freshness требует source weight не ниже 12.

4. **Geo alias / city query fix**
   - Для городов добавлены disambiguated query bases: `Tbilisi Georgia`, `Paris France`, `Kyiv Ukraine`, etc.

5. **FAQ/support filter**
   - Для brand/company и technology тем страницы `/support`, `/faq`, `/help`, customer FAQ, troubleshooting и similar evergreen pages режутся как не-news.

6. **Debug dump fix**
   - При `APP_DEBUG=true` JSON dumps включаются автоматически даже если `SEARCH_DEBUG_DUMP_ENABLED` забыли поставить.

7. **Token-safe logging**
   - Снижен уровень шумных `httpx/httpcore/telegram` логгеров, чтобы не тащить Bot API URL с токеном в debug log.

## Бюджет

Soft target остаётся `$0.07`, hard cap — `$0.10`. Третий pass всё ещё rescue-only.
