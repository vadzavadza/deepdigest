# Quality Engine v5.2 — freshness/recall balance

Эта версия продолжает v5.1. Цель: не возвращать старьё, но и не убивать поиск до нуля из-за слишком жёсткого требования verified publish date.

## Что исправлено

1. **Сбалансированный freshness fallback**
   - По умолчанию по-прежнему предпочитается подтверждённая дата публикации из metadata или URL.
   - Если строгий режим дал слишком мало кандидатов, движок может использовать OpenRouter search annotation/snippet как weak-freshness fallback.
   - Такой fallback разрешён только для кандидатов с высоким directness/article confidence.
   - В итоговом дайджесте weak-freshness кандидаты ограничены: по умолчанию максимум 1.

2. **News hub guard**
   - Блокируются страницы вида `Microsoft News | Windows Central`, `Bitcoin News Today`, `Latest X News`.
   - Это не статьи, а разделы/лендинги, даже если сайт подсовывает свежий modified/datePublished.

3. **Cyrillic / Ukrainian story dedup**
   - Дедупликация теперь понимает кириллицу и украинские токены.
   - Матч-репорты вроде `Шахтар — Зоря` из разных источников должны склеиваться в один сюжет.

4. **Generic software/technology class**
   - Темы вроде `python` теперь считаются software/technology, а не generic broad topic.
   - Добавлены позитивные контексты: programming, software, release, security, developer.
   - Добавлены негативные контексты для Python как животного: snake, reptile, zoo.

5. **Generic esports acronym handling**
   - Темы с `CS`, `CS2`, `Dota`, `Valorant` и похожими маркерами идут в esports strategy.
   - Это не хардкод под BLAST; это общий класс для киберспортивных запросов.

## Новые настройки .env

```env
OPENROUTER_ALLOW_SEARCH_SNIPPET_FALLBACK=true
OPENROUTER_SEARCH_SNIPPET_FALLBACK_MIN_DIRECTNESS=12
OPENROUTER_SEARCH_SNIPPET_FALLBACK_MIN_CONFIDENCE=2
OPENROUTER_MAX_WEAK_FRESHNESS_ITEMS_PER_DIGEST=1
```

## Важная логика

v5.1 был слишком строгим: без verified date он часто давал 0.
v5.2 делает так:

1. Сначала строгий проход: verified publish date only.
2. Если кандидатов мало — rescue pass без нового OpenRouter-запроса.
3. Rescue pass берёт только сильные search-annotation кандидаты.
4. Эти кандидаты получают штраф в ranking и лимитируются в публикации.

Идея: лучше 1 слабоподтверждённый, но очень релевантный свежий кандидат, чем 0 по темам вроде крупных политиков/киберспорта/технологий. Но старые статьи и hub pages всё равно режутся.
