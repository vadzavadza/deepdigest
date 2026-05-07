# Quality Engine v5.1 — Freshness Guard

Цель патча: убрать ситуацию, когда бот выдаёт прошлогодние или старые статьи как `latest digest`.

## Что было не так

В v5 у OpenRouter source был опасный fallback: если статья была найдена через web-search, но HTML страницы не отдавался, блокировался или не содержал нормальной даты публикации, движок мог поставить `published_at = now`.

Из-за этого старая статья могла выглядеть свежей внутри пайплайна.

## Что изменено

### 1. Больше не подделываем дату публикации

Если дата публикации не найдена и не подтверждена, кандидат по умолчанию отбрасывается.

Подтверждёнными считаются:

- `article:published_time` / `datePublished` / `<time datetime=...>` и похожие metadata;
- дата в URL, например `/2026/04/24/...`.

`Last-Modified` по умолчанию НЕ считается надёжной датой публикации, потому что старые статьи часто обновляются сайтом технически.

### 2. Добавлен freshness floor

Даже если тема запущена впервые с широким окном, статья не может быть старше:

```env
OPENROUTER_MAX_ARTICLE_AGE_HOURS=168
```

То есть по умолчанию максимум 7 дней.

Для повторного запуска окно ещё строже: максимум последние 48 часов, чтобы бот не доставал слабые старые остатки сразу после первого дайджеста.

### 3. Усилен prompt для OpenRouter search

Теперь запросы прямо требуют статьи, опубликованные внутри окна времени, и просят не возвращать старые архивы или страницы без даты.

### 4. Query variants теперь содержат `published after YYYY-MM-DD`

Раньше первый запуск мог писать слишком расплывчато: `recent news`.
Теперь каждый query variant содержит явную нижнюю границу даты.

### 5. Добавлены debug rejection reasons

Новые причины отказа:

- `missing_verified_publish_date`
- `outside_freshness_window:<source>:<date>`
- `future_publish_date:<source>:<date>`
- `fallback_missing_verified_date:<reason>`
- `fallback_outside_freshness_window:<source>:<date>`

## Новые настройки `.env`

```env
OPENROUTER_MAX_ARTICLE_AGE_HOURS=168
OPENROUTER_REQUIRE_VERIFIED_PUBLISH_DATE=true
OPENROUTER_ALLOW_WEAK_PUBLISH_DATES=false
OPENROUTER_ALLOW_UNDATED_FALLBACK=false
OPENROUTER_FUTURE_SKEW_HOURS=12
```

Рекомендуемый режим — оставить так.

Если окажется, что некоторые хорошие сайты часто не отдают дату, можно временно включить:

```env
OPENROUTER_ALLOW_WEAK_PUBLISH_DATES=true
```

Но лучше сначала посмотреть логи rejection reasons.

## Что проверено

- `python -m compileall -q app tests` — PASS
- `pytest -q` — PASS, 29 tests
- zip integrity — PASS

## Важно

Этот патч не делает упор на конкретные темы. Он добавляет универсальное правило: `latest digest` не должен доверять статьям без подтверждённой свежей даты.
