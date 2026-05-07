# Quality Engine v6 — Universal Search Core

Цель v6: не подгонять бота под конкретные темы, а сделать более устойчивое универсальное поисковое ядро новостей.

## Что изменено

1. **CandidateStatus вместо тупого pass/fail**

Теперь кандидат получает один из статусов:

- `accepted` — подтверждённая дата и нормальное качество;
- `weak_but_usable` — прямой сильный кандидат из OpenRouter search snippet, но без подтверждённой даты;
- `old` — слишком старая статья;
- `hub_page` — страница-раздел / news hub;
- `wrong_entity` — не та сущность;
- `rejected` — остальные причины отказа.

2. **Гибкая freshness-модель**

Больше не режем все статьи старше 7 дней сразу. Теперь:

- 0–7 дней — лучший вариант;
- 8–30 дней — можно брать, если статья verified и прямой релевантности достаточно;
- старше 30 дней — отбрасывается;
- без даты — можно только как `weak_but_usable`, если OpenRouter дал сильный snippet и тема прямо в заголовке/описании.

3. **Generic suffix normalization**

Пользовательские формы вроде `NAVI TEAM`, `Rome city`, `OpenAI official` не должны превращаться в обязательные точные фразы. Например `NAVI TEAM` нормализуется в `navi`, но raw-вариант всё равно используется в query plan.

4. **Search snippet rescue внутри одного запуска**

Если сайт блокирует HTML или не отдаёт дату, но OpenRouter search annotation содержит прямой title/snippet, кандидат может пройти как weak freshness. Такие статьи штрафуются в ranking и ограничиваются настройкой `OPENROUTER_MAX_WEAK_FRESHNESS_ITEMS_PER_DIGEST`.

5. **Лучшие debug-логи**

Добавлен `candidate_decision`, где видно:

- status;
- reason;
- directness_score;
- article_confidence;
- freshness_verified;
- published_at_source.

## Что v6 НЕ делает

- Не добавляет правила вида `if topic == "bitcoin"`.
- Не подгоняет результаты под NAVI/Kyiv/bitcoin/Dyson/etc.
- Не отключает freshness guard полностью.
- Не добивает дайджест мусором ради количества.

## Новые настройки

```env
OPENROUTER_VERIFIED_HARD_MAX_ARTICLE_AGE_HOURS=720
OPENROUTER_FOLLOWUP_HARD_MAX_ARTICLE_AGE_HOURS=72
```

Остальные настройки от v5.4 остаются актуальными.

## Как тестировать

Сначала проверь пары и широкие темы:

```text
bitcoin
Kyiv / Київ / Киев
NAVI TEAM / NAVI / Natus Vincere
Dyson / Дайсон / дайсан
Paris / Париж
Trump / Трамп
```

Главное смотреть:

1. стало ли меньше ложных нулей;
2. не полезли ли реально старые статьи;
3. не проходят ли news hub pages;
4. появляются ли `weak_but_usable` только когда verified-кандидатов мало;
5. повторный запуск сразу после нормального дайджеста не должен слать старые остатки.
