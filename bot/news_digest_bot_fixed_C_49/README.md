# News Digest Bot — Rebuild v3

Это **пересобранный фундамент проекта** под новые требования:

- пользователь один раз задаёт тему, время и язык;
- бот сам каждый день присылает **топ-5** новостей по теме;
- поиск источников отделён от обработки сюжетов;
- источник №1 для MVP — **OpenRouter Web Search**;
- архитектура сразу готова к будущим source adapters:
  - Telegram channels
  - RSS / news sitemaps
  - custom site crawlers
  - другие источники
- одинаковые сюжеты не дублируются;
- при совпадении источников приоритет: **EN > DE > Other > RU**;
- вчерашний сюжет не должен снова приходить как новый только из-за другого сайта.

## Что это сейчас

Это **не пустой шаблон** и **не финальный прод на 100%**.
Это уже собранная база, на которой мы теперь будем запускать проект шаг за шагом.

## Что уже есть

- FastAPI сервис
- Telegram bot layer
- PostgreSQL models + repositories
- scheduler layer
- multi-source architecture
- Source Registry
- Source Collection Service
- story-centric processing pipeline
- OpenRouter LLM provider
- OpenRouter web search source adapter
- tests
- Docker Compose
- очень простой стартовый гайд на русском

## Главная архитектура

```text
Source Adapters -> Source Collection -> Processing -> LLM -> Publishing
```

### Source Adapters

Каждый источник живёт отдельно и возвращает единый формат `RawSourceItem`.
Сейчас реально подключён каркас для `openrouter_web_search`.
Позже без ломки ядра можно подключить:

- Telegram channels
- RSS
- custom sites
- другие источники

### Processing

Ядро проекта:

- нормализация
- story grouping
- dedup
- ranking
- memory через `stories + sent_stories`
- выбор основного источника
- подготовка payload для публикации

## Что ещё останется доделать после запуска

- живой `.env` на твоих ключах
- первая локальная загрузка через Docker
- реальная проверка OpenRouter web search на твоём аккаунте
- FSM создания темы в боте
- migrations / Alembic runtime
- end-to-end ручной прогон первой темы
- потом polishing

## С чего начать

Открой файл `START_HERE_RU.md`.
Он написан специально очень маленькими шагами.


## Fix6
- Channels menu now lists publication channels and can save the current chat as a publication target for MVP.


## UX update in fix7

- Personal chat is now the default destination for every user.
- Saved publication channels are optional and appear only as an extra choice during topic creation.


## Что добавлено в big stage
- Кнопка **▶️ Запустить сейчас** у темы
- Ручной поиск новостей по теме через OpenRouter web search source
- Отправка найденных новостей в личный чат по умолчанию
- Список тем, карточка темы и удаление
- Каналы публикации остаются как дополнительная опция

## Что ещё не финально
- Автоматическое ежедневное расписание ещё не доведено до продуктового UX
- Источники Telegram-каналов как source layer пока не включены
- Ранжирование и dedup работают как MVP-версия


## Search fix stage

This stage improves OpenRouter web search integration by using the current `openrouter:web_search` server tool first and falling back to the legacy `web` plugin if needed. It also softens LLM failures so manual runs are easier to debug.
