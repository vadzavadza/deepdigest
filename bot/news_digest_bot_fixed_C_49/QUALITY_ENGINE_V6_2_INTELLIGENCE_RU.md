# v6.2 Universal News Intelligence Layer

Цель v6.2 — не подгонка под отдельные темы, а усиление универсального понимания типа новости.

## Что изменено

1. **Topic Classifier v2**
   - `sports_team` — футбольные/спортивные клубы и команды;
   - `brand_company` — бренды и компании;
   - `entertainment_company` — киностудии, студии, медиакомпании;
   - `ambiguous_acronym` — короткие неоднозначные темы вроде `CS`, `AI`, `X`.

2. **Query Planner по vertical-типу**
   - sports team: матчи, трансферы, травмы, тренер, лига;
   - brand/company: recalls, product launch, earnings, production, regulation;
   - entertainment company: film slate, releases, box office, production, lawsuits;
   - ambiguous acronym: осторожные запросы, с требованием контекста.

3. **Vertical Source Authority**
   Источники теперь оцениваются не одной общей таблицей, а с поправкой на тип темы:
   - спорт: спортивные источники получают бонус;
   - авто/бренды: авто-источники получают бонус, review/guides понижаются;
   - кино/студии: Variety/Deadline/THR/TheWrap выше слабых агрегаторов;
   - crypto: CoinDesk/Cointelegraph/Decrypt/The Block/CryptoSlate выше биржевых/price pages.

4. **Content Type Filter**
   Review, buyer guide, “I drove...”, “for a week”, price pages и hub pages не должны проходить как ordinary latest news.

5. **Ambiguous Acronym Handling**
   `CS` больше не считается автоматически командой/организацией. Для Counter-Strike нужны контекстные сигналы: `CS2`, `Counter-Strike`, `esports`, `roster`, `tournament`, `BLAST`, `IEM`, `ESL`.

## Что НЕ сделано

- Не переписывал Telegram/БД/scheduler.
- Не делал правила вида `if topic == Real Madrid`.
- Живой OpenRouter/Telegram в этой среде не запускался.

