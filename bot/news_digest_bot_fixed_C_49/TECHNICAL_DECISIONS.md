# Technical Decisions — Rebuild v3

## 1. Product goal

Пользователь один раз задаёт тему и время.
Дальше бот сам ежедневно присылает краткий топ новостей по теме.

## 2. Source strategy

Слой поиска источников отделён от слоя обработки.
Это обязательное решение.

### Why

Сегодня источник поиска — OpenRouter web search.
Завтра мы должны иметь возможность добавить:
- Telegram channels
- RSS
- custom websites
- другие источники

Без переписывания dedup/ranking/publishing.

## 3. Core architecture

```text
Source Adapters -> Source Collection -> Processing -> LLM -> Publishing
```

## 4. Unified input object

Все источники отдают `RawSourceItem`.
Мы не привязываем ядро только к `RawArticle`, потому что Telegram channels потом не обязаны выглядеть как обычная статья.

## 5. Story-centric product rule

Публикация строится вокруг story, а не вокруг URL.
Один и тот же сюжет не должен публиковаться повторно на следующий день только потому, что найден другой URL.

## 6. Ranking rule

Приоритет языков:
- EN = 100
- DE = 90
- Other = 60
- RU = 40

Дальше учитываются качество источника и свежесть.

## 7. LLM role

LLM не является единственным местом, где живёт бизнес-логика.
LLM используется для:
- relevance check
- summary
- translation
- semantic duplicate check в спорных случаях

## 8. MVP scope

### Included now
- OpenRouter web search source
- Source registry
- Source collection service
- Processing pipeline
- Memory and dedup skeleton
- Telegram publishing layer

### Later
- Telegram channel source adapter
- RSS source adapter
- custom site source adapter
- richer topic-creation UX
