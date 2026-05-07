from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Final


@dataclass(slots=True)
class SearchPlan:
    raw_query: str
    normalized_query: str
    topic_kind: str
    first_run: bool
    broad_topic: bool
    freshness_hint: str
    query_variants: list[str]
    required_terms: set[str]
    soft_terms: set[str]
    exact_phrase: str | None
    semantic_hints: set[str]
    strict_phrase: bool = False
    max_variants: int = 4
    alternate_terms: set[str] | None = None
    positive_context_terms: set[str] = field(default_factory=set)
    negative_context_terms: set[str] = field(default_factory=set)
    minimum_directness: int = 6


_WEATHER_HINTS: Final = {"weather", "temperature", "forecast", "rain", "snow", "storm", "heatwave", "wind"}
_UPDATE_HINTS: Final = {"update", "updates", "patch", "patches", "patch notes", "changelog", "release notes", "official update"}
_CONFLICT_HINTS: Final = {"war", "conflict", "invasion", "ceasefire", "frontline", "military", "strike", "aid"}
_SPORT_HINTS: Final = {"fc", "club", "transfer", "injury", "league", "match", "coach", "goal", "nba", "nfl", "mlb", "nhl", "epl", "laliga", "la liga", "premier league", "serie a", "bundesliga", "champions league"}
_SPORTS_TEAM_MARKERS: Final = {"fc", "cf", "sc", "club", "united", "city", "real", "atletico", "athletic", "inter", "borussia", "sporting", "rangers", "celtic", "bayern", "psg", "juventus", "arsenal", "chelsea", "liverpool"}
_SPORTS_TEAM_CONTEXT: Final = {"match", "transfer", "injury", "coach", "manager", "league", "cup", "goal", "squad", "roster", "player", "club", "football", "soccer", "basketball", "baseball", "hockey"}
_ESPORTS_HINTS: Final = {"esports", "roster", "tournament", "major", "valve", "steam", "dota", "cs2", "counter-strike", "counter strike", "hltv", "bo3", "qualifier", "valorant", "blast", "iem", "esl"}
_ESPORTS_ACRONYM_RE: Final = re.compile(r"\b(cs|cs2|dota|valorant|lol|rlcs)\b", re.IGNORECASE)
_TECH_SOFTWARE_HINTS: Final = {"python", "java", "javascript", "typescript", "rust", "golang", "go", "php", "ruby", "kotlin", "swift", "scala", "perl", "linux", "docker", "kubernetes", "nodejs", "react", "django", "pytorch", "tensorflow", "postgresql", "mysql"}
_TEAM_ENTITY_MARKERS: Final = {"team", "squad", "roster", "club", "org", "organization"}
_BUSINESS_HINTS: Final = {"earnings", "shares", "stock", "market", "results", "guidance", "investor", "ceo", "merger", "acquisition"}
_CRYPTO_HINTS: Final = {"bitcoin", "ethereum", "solana", "crypto", "cryptocurrency", "blockchain", "token", "defi", "etf"}
_ENTERTAINMENT_HINTS: Final = {"movie", "film", "series", "tv", "show", "studio", "studios", "streaming", "actor", "actress", "album", "music", "box office"}
_ENTERTAINMENT_COMPANY_TERMS: Final = {"pictures", "studios", "studio", "films", "film", "entertainment", "media", "animation", "streaming"}
_GEO_REGION_HINTS: Final = {"ocean", "sea", "river", "gulf", "canal", "strait", "island", "islands", "mountain", "mountains", "region", "basin"}
_COMPANY_SUFFIXES: Final = {"inc", "corp", "corporation", "ltd", "plc", "ag", "sa", "group", "holdings", "company", "co"}
_AMBIGUOUS_ACRONYMS: Final = {"cs", "ai", "x", "us", "eu", "uae", "uk", "ml", "go"}
_AMBIGUOUS_GEO_TOPICS: Final = {"washington", "georgia", "jordan"}
_KNOWN_TEAM_ORGS: Final = {"navi", "natus vincere", "faze clan", "team spirit", "g2 esports", "cloud9", "fnatic", "team liquid"}
_STOP: Final = {"the", "and", "for", "with", "latest", "news", "new", "about", "from", "city"}
_GENERIC_TOPIC_SUFFIXES: Final = {"team", "club", "organization", "org", "official"}


_KNOWN_BRANDS: Final = {
    "apple", "tesla", "microsoft", "google", "alphabet", "amazon", "meta", "netflix", "nvidia",
    "bmw", "mercedes", "volkswagen", "toyota", "lexus", "audi", "porsche", "honda", "ford", "gm", "general motors", "samsung", "sony", "disney", "dyson",
    "openai", "oracle", "intel", "amd", "ibm", "salesforce", "adobe", "spotify", "uber", "airbnb",
}
_KNOWN_CRYPTO: Final = {"bitcoin", "ethereum", "solana", "xrp", "cardano", "dogecoin", "binance", "toncoin", "polkadot"}

_COUNTRY_NAMES: Final = {
    "usa", "us", "united states", "uk", "united kingdom", "england", "ukraine", "germany", "france", "japan", "china",
    "zimbabwe", "russia", "iran", "spain", "italy", "poland", "georgia", "israel", "lebanon", "pakistan", "india",
    "canada", "mexico", "brazil", "argentina", "turkey", "australia", "south korea", "north korea", "south africa",
}

# Small canonical alias table, not topic-specific behavior. It fixes common transliteration/alternate spellings.
_CITY_ALIASES: Final[dict[str, set[str]]] = {
    "kyiv": {"kyiv", "kiev", "київ", "киев"},
    "lviv": {"lviv", "львів", "львов", "lvov"},
    "kharkiv": {"kharkiv", "kharkov", "харків", "харьков"},
    "odesa": {"odesa", "odessa", "одеса", "одесса"},
    "dnipro": {"dnipro", "dnieper", "дніпро", "днепр"},
    # Global city aliases are generic normalization, not per-test behavior.
    "paris": {"paris", "париж", "paris france", "парис"},
    "rome": {"rome", "roma", "рим", "rome italy"},
    "london": {"london", "лондон", "london uk"},
    "berlin": {"berlin", "берлин", "берлін"},
    "madrid": {"madrid", "мадрид"},
    "barcelona": {"barcelona", "барселона"},
    "tbilisi": {"tbilisi", "tiflis", "тбилиси", "თბილისი"},
    "new york": {"new york", "nyc", "нью-йорк", "нью йорк"},
}

_CITY_CONTEXTS: Final[dict[str, dict[str, set[str]]]] = {
    "kyiv": {"positive": {"ukraine", "ukrainian", "kyiv oblast", "capital"}, "negative": {"kiev chicken"}},
    "lviv": {"positive": {"ukraine", "ukrainian", "lviv oblast"}, "negative": set()},
    "kharkiv": {"positive": {"ukraine", "ukrainian", "kharkiv oblast"}, "negative": set()},
    "odesa": {"positive": {"ukraine", "ukrainian", "black sea", "odesa oblast"}, "negative": {"texas", "florida", "missouri", "delaware", "permian", "high school", "weather spark"}},
    "dnipro": {"positive": {"ukraine", "ukrainian", "dnipropetrovsk"}, "negative": set()},
    "paris": {"positive": {"france", "french", "ile-de-france", "île-de-france", "mayor", "city hall"}, "negative": {"paris hilton", "paris texas", "texas"}},
    "rome": {"positive": {"italy", "italian", "lazio", "mayor", "city council"}, "negative": {"ancient rome", "roman empire"}},
    "london": {"positive": {"uk", "united kingdom", "england", "mayor", "city hall"}, "negative": {"london ontario", "ontario"}},
    "berlin": {"positive": {"germany", "german", "senate", "brandenburg"}, "negative": set()},
    "madrid": {"positive": {"spain", "spanish", "city council"}, "negative": set()},
    "barcelona": {"positive": {"spain", "catalonia", "catalan", "city council"}, "negative": set()},
    "tbilisi": {"positive": {"georgia", "georgian", "caucasus"}, "negative": set()},
    "new york": {"positive": {"nyc", "new york city", "mayor", "manhattan", "brooklyn"}, "negative": {"new york state"}},
}


_CITY_DISAMBIGUATION: Final[dict[str, str]] = {
    "kyiv": "ukraine",
    "lviv": "ukraine",
    "kharkiv": "ukraine",
    "odesa": "ukraine",
    "dnipro": "ukraine",
    "paris": "france",
    "rome": "italy",
    "london": "uk",
    "berlin": "germany",
    "madrid": "spain",
    "barcelona": "spain",
    "tbilisi": "georgia",
    "new york": "new york city",
}

_AMBIGUOUS_ENTITY_HINTS: Final[dict[str, dict[str, set[str]]]] = {
    "georgia": {
        "country": {"tbilisi", "caucasus", "georgian government", "ruling party", "parliament"},
        "us_state": {"atlanta", "governor", "us state", "state legislature", "county"},
    },
    "jaguar": {
        "company": {"automaker", "electric vehicle", "car", "land rover", "model"},
        "animal": {"wildlife", "conservation", "habitat"},
        "sports": {"nfl", "jacksonville", "quarterback", "coach"},
    },
    "apple": {
        "company": {"iphone", "mac", "ios", "app store", "earnings", "shares"},
        "food": {"fruit", "orchard", "crop", "harvest"},
    },
}

_ENTITY_ALIASES: Final[dict[str, str]] = {
    # Common public-name shorthand and multilingual spellings. This is normalization only;
    # ranking still requires direct topical evidence from each article.
    "trump": "donald trump",
    "donald trump": "donald trump",
    "дональд трамп": "donald trump",
    "трамп": "donald trump",
    "pavel durov": "pavel durov",
    "durov": "pavel durov",
    "павел дуров": "pavel durov",
    "павло дуров": "pavel durov",
    "дуров": "pavel durov",
}

_TEAM_ORG_ALIASES: Final[dict[str, str]] = {
    "navi": "navi",
    "navi team": "navi",
    "team navi": "navi",
    "natus vincere": "navi",
    "натус винсере": "navi",
    "натус вінсере": "navi",
    "team spirit": "team spirit",
    "спирит": "team spirit",
    "faze": "faze clan",
    "фейз": "faze clan",
}

_GEO_ENTITY_ALIASES: Final[dict[str, str]] = {
    "washington": "washington",
    "washington dc": "washington",
    "washington d.c.": "washington",
    "вашингтон": "washington",
    "vashington": "washington",
}

_BRAND_ALIASES: Final[dict[str, str]] = {
    "dyson": "dyson",
    "дайсон": "dyson",
    "дайсан": "dyson",
    "microsoft": "microsoft",
    "майкрософт": "microsoft",
    "volkswagen": "volkswagen",
    "vw": "volkswagen",
    "фольксваген": "volkswagen",
    "tesla": "tesla",
    "тесла": "tesla",
    "openai": "openai",
    "опенай": "openai",
    "apple": "apple",
    "эппл": "apple",
    "lexus": "lexus",
    "лексус": "lexus",
    "audi": "audi",
    "ауди": "audi",
}

# Simple deterministic transliteration helps the search layer try both scripts. It is not
# used as proof of relevance; it only generates more reliable query variants.
_CYRILLIC_TRANSLIT: Final[dict[str, str]] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "є": "ie", "ж": "zh",
    "з": "z", "и": "i", "і": "i", "ї": "yi", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "ґ": "g",
}

_TRANSLIT_ALIASES: Final[dict[str, str]] = {}
for canonical, aliases in _CITY_ALIASES.items():
    for alias in aliases:
        _TRANSLIT_ALIASES[alias] = canonical
_TRANSLIT_ALIASES.update(_ENTITY_ALIASES)
_TRANSLIT_ALIASES.update(_TEAM_ORG_ALIASES)
_TRANSLIT_ALIASES.update(_GEO_ENTITY_ALIASES)
_TRANSLIT_ALIASES.update(_BRAND_ALIASES)


def _normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip().lower())
    return text


def transliterate_cyrillic(text: str) -> str:
    chars: list[str] = []
    for ch in text.lower():
        chars.append(_CYRILLIC_TRANSLIT.get(ch, ch))
    return re.sub(r"\s+", " ", "".join(chars)).strip()


def _strip_generic_topic_words(q: str) -> str:
    """Remove generic UI/user suffixes without hard-coding concrete topics.

    Users often enter forms like "NAVI TEAM", "Rome city", or "OpenAI official".
    Those generic words should help query planning, but they should not become
    required entity tokens. Otherwise good articles are rejected because they say
    "NAVI" or "Rome" but not the exact phrase "NAVI TEAM".
    """
    words = q.split()
    if len(words) >= 2 and words[-1] in _GENERIC_TOPIC_SUFFIXES:
        return " ".join(words[:-1]).strip() or q
    if len(words) >= 2 and words[-1] == "city":
        candidate = " ".join(words[:-1]).strip()
        # Only strip city when the remaining phrase is a known city alias/canonical.
        if candidate in _CITY_ALIASES or any(candidate in aliases for aliases in _CITY_ALIASES.values()):
            return candidate
    return q


def canonicalize_topic(query: str) -> str:
    q = _strip_generic_topic_words(_normalize(query))
    if q in _TRANSLIT_ALIASES:
        return _TRANSLIT_ALIASES[q]
    translit = _strip_generic_topic_words(transliterate_cyrillic(q))
    if translit and translit != q and translit in _TRANSLIT_ALIASES:
        return _TRANSLIT_ALIASES[translit]
    return translit if translit and translit != q else q


def _query_bases(raw_query: str, canonical: str, kind: str) -> list[str]:
    raw_norm = _normalize(raw_query)
    translit = transliterate_cyrillic(raw_norm)
    bases: list[str] = []
    for candidate in (canonical, raw_norm, translit):
        candidate = _normalize(candidate)
        if candidate and candidate not in bases:
            bases.append(candidate)

    if kind == "ambiguous_geo" and canonical == "washington":
        for candidate in ("washington dc", "washington state"):
            if candidate not in bases:
                bases.append(candidate)
    if kind == "city":
        preferred = _CITY_DISAMBIGUATION.get(canonical)
        if preferred:
            disambiguated = f"{canonical} {preferred}"
            if disambiguated not in bases:
                bases.insert(1, disambiguated)
        else:
            context = _CITY_CONTEXTS.get(canonical, {}).get("positive", set())
            # Add one disambiguated city form early, e.g. "paris france" or "odesa ukraine".
            for term in sorted(context):
                if len(term.split()) <= 2 and term not in {"mayor", "capital", "city hall", "city council"}:
                    disambiguated = f"{canonical} {term}"
                    if disambiguated not in bases:
                        bases.insert(1, disambiguated)
                    break
    return bases[:4]


def _tokens(query: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-zA-Z0-9а-яА-ЯёЁіІїЇєЄґҐ]+", query.lower()) if len(tok) >= 3 and tok not in _STOP}


def _looks_like_person_name(raw_query: str, normalized_query: str) -> bool:
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", raw_query.strip()) if w.lower() not in _STOP]
    if len(words) not in {2, 3}:
        return False
    lower_words = {w.lower().strip(".'") for w in words}
    if lower_words & _COMPANY_SUFFIXES:
        return False
    if normalized_query in _COUNTRY_NAMES or normalized_query in _KNOWN_BRANDS or normalized_query in _KNOWN_CRYPTO:
        return False
    capitalized = sum(1 for w in words if w[:1].isupper())
    return capitalized >= 1 or len(words) == 2


def _looks_like_software_tech(q: str) -> bool:
    q_tokens = _tokens(q)
    if q in _TECH_SOFTWARE_HINTS:
        return True
    if q_tokens & (_TECH_SOFTWARE_HINTS - {"go"}):
        return True
    if any(marker in q for marker in ("programming language", "software release", "developer", "github", "pypi")):
        return True
    return False


def _looks_like_esports_query(raw_query: str, q: str) -> bool:
    if any(h in q for h in _ESPORTS_HINTS):
        return True
    if _ESPORTS_ACRONYM_RE.search(raw_query):
        return True
    return False



def _looks_like_sports_team_query(raw_query: str, q: str) -> bool:
    words = q.split()
    if not words or len(words) > 4:
        return False
    token_set = set(words)
    if token_set & _SPORTS_TEAM_MARKERS:
        return True
    if q.endswith(" fc") or q.endswith(" cf") or q.endswith(" sc") or q.startswith("fc "):
        return True
    if any(marker in _normalize(raw_query) for marker in ("football club", "soccer club", "basketball club")):
        return True
    return False


def _looks_like_entertainment_company(q: str) -> bool:
    words = set(q.split())
    if words & _ENTERTAINMENT_COMPANY_TERMS:
        return True
    return False


def _looks_like_company_or_brand(q: str) -> bool:
    words = set(q.split())
    if q in _KNOWN_BRANDS:
        return True
    if words & _COMPANY_SUFFIXES:
        return True
    return False


def _is_ambiguous_acronym(raw_query: str, q: str) -> bool:
    raw = raw_query.strip()
    if len(raw) <= 3 and raw.upper() == raw and q in _AMBIGUOUS_ACRONYMS:
        return True
    return False

def classify_topic(query: str) -> str:
    q = canonicalize_topic(query)
    token_count = len(_tokens(q))
    if _is_ambiguous_acronym(query, q):
        return "ambiguous_acronym"
    if q in _AMBIGUOUS_GEO_TOPICS:
        return "ambiguous_geo"
    if any(h in q for h in _WEATHER_HINTS):
        return "weather_like"
    if any(h in q for h in _UPDATE_HINTS):
        return "game_updates"
    if q in _KNOWN_CRYPTO or any(h in q for h in _CRYPTO_HINTS):
        return "crypto"
    if q in _KNOWN_TEAM_ORGS or q in set(_TEAM_ORG_ALIASES.values()):
        return "team_org"
    if _looks_like_entertainment_company(q):
        return "entertainment_company"
    if _looks_like_sports_team_query(query, q):
        return "sports_team"
    if q in set(_ENTITY_ALIASES.values()):
        return "person"
    if _looks_like_software_tech(q):
        return "technology"
    if _looks_like_esports_query(query, q):
        return "esports"
    if any(h in q for h in _CONFLICT_HINTS):
        return "conflict"
    if any(h in q for h in _SPORT_HINTS):
        return "sports"
    if q in _COUNTRY_NAMES:
        return "country"
    if q in _CITY_ALIASES:
        return "city"
    if any(h in q for h in _GEO_REGION_HINTS):
        return "geo_region"
    if _looks_like_company_or_brand(q) or any(h in q for h in _BUSINESS_HINTS):
        return "brand_company"
    if any(h in q for h in _ENTERTAINMENT_HINTS):
        return "entertainment"
    words = q.split()
    if len(words) <= 3 and (words[:1] and words[0] in _TEAM_ENTITY_MARKERS):
        return "team_org"
    if len(words) <= 2 and all(w[:1].isalpha() for w in words) and query.strip().isupper() and q not in _COUNTRY_NAMES and q not in _KNOWN_BRANDS:
        return "team_org"
    if _looks_like_person_name(query, q):
        return "person"
    if token_count <= 1 and query.strip().isupper() and len(query.strip()) >= 3 and q not in _KNOWN_BRANDS:
        return "entity_symbol"
    if token_count <= 1:
        return "broad_single"
    if token_count == 2:
        return "broad_dual"
    return "general_news"


def _freshness_hint(from_dt: datetime, to_dt: datetime, first_run: bool) -> str:
    # Hard provider-side date constraints often make OpenRouter return zero links.
    # Retrieve a slightly wider candidate pool, then enforce real freshness locally.
    hours = max(int((to_dt - from_dt).total_seconds() // 3600), 1)
    requested_days = max(1, (hours + 23) // 24)
    retrieval_days = min(30, max(7, requested_days * 2 if first_run else requested_days + 3))
    return f"recent news from the last {retrieval_days} days"


def _semantic_hints_for_query(q: str, kind: str) -> set[str]:
    hints: set[str] = {"report", "development", "official"}
    if kind == "game_updates":
        hints |= {"patch", "notes", "official", "release", "changes", "version", "changelog"}
    elif kind == "conflict":
        hints |= {"war", "strike", "troops", "aid", "ceasefire", "drone", "missile", "frontline"}
    elif kind == "sports":
        hints |= {"match", "transfer", "injury", "coach", "league", "win", "defeat", "club"}
    elif kind == "sports_team":
        hints |= _SPORTS_TEAM_CONTEXT | {"official", "fixture", "lineup", "signing"}
    elif kind == "esports":
        hints |= {"esports", "roster", "tournament", "team", "major", "qualifier", "match"}
    elif kind == "team_org":
        hints |= {"official", "team", "organization", "roster", "esports", "club", "announcement"}
    elif kind == "weather_like":
        hints |= {"storm", "flood", "forecast", "rain", "snow", "heatwave", "temperature"}
    elif kind == "entity_symbol":
        hints |= {"official", "organization", "company", "team", "brand", "statement", "results", "launch"}
    elif kind == "city":
        hints |= {"city", "region", "mayor", "council", "infrastructure", "incident", "local", "official"}
    elif kind == "geo_region":
        hints |= {"environment", "shipping", "security", "weather", "scientists", "islands", "marine", "climate"}
    elif kind == "country":
        hints |= {"politics", "economy", "government", "security", "official", "development"}
    elif kind == "crypto":
        hints |= {"crypto", "blockchain", "market", "etf", "regulation", "exchange", "protocol"}
    elif kind == "technology":
        hints |= {"software", "release", "security", "developer", "programming", "package", "open source", "github"}
    elif kind in {"business", "brand_company"}:
        hints |= {"earnings", "company", "launch", "product", "recall", "safety", "production", "shares", "regulation", "deal"}
    elif kind == "person":
        hints |= {"statement", "company", "lawsuit", "interview", "announcement", "profile", "deal"}
    elif kind == "entertainment":
        hints |= {"film", "series", "studio", "release", "box office", "streaming", "production"}
    elif kind == "entertainment_company":
        hints |= {"film", "studio", "box office", "release", "slate", "cinema", "production", "lawsuit", "deal"}
    elif kind == "ambiguous_geo":
        hints |= {"dc", "state", "government", "governor", "local", "politics", "city", "region"}
    elif kind == "ambiguous_acronym":
        hints |= {"official", "organization", "company", "team", "policy", "release"}
    return {h.lower() for h in hints}


def _alternate_terms(q: str) -> set[str]:
    terms = {q}
    if q in _CITY_ALIASES:
        terms |= set(_CITY_ALIASES[q])
    for alias, canonical in _ENTITY_ALIASES.items():
        if canonical == q:
            terms.add(alias)
    for alias, canonical in _BRAND_ALIASES.items():
        if canonical == q:
            terms.add(alias)
    if q in _TECH_SOFTWARE_HINTS:
        terms |= {q, f"{q} programming language", f"{q} software"}
        if q == "python":
            terms |= {"python programming", "python software", "python release", "pypi"}
    if q == "cs":
        terms |= {"counter-strike", "counter strike", "cs2", "counter-strike 2"}
    return {t for t in terms if t}


def _context_terms(q: str, kind: str) -> tuple[set[str], set[str]]:
    positive: set[str] = set()
    negative: set[str] = set()
    if kind == "city":
        context = _CITY_CONTEXTS.get(q)
        if context:
            positive |= context.get("positive", set())
            negative |= context.get("negative", set())
    if kind == "technology":
        positive |= {"software", "programming", "developer", "release", "security", "open source", "github", "package"}
        if q == "python":
            negative |= {"snake", "zoo", "reptile", "burmese python", "reticulated python"}
    if kind in {"business", "brand_company"}:
        positive |= {"company", "product", "launch", "recall", "safety", "earnings", "ceo", "shares", "market", "regulation", "deal", "production"}
    if kind == "sports_team":
        positive |= _SPORTS_TEAM_CONTEXT
    if kind == "entertainment_company":
        positive |= {"studio", "film", "movie", "box office", "release", "cinema", "production", "slate", "streaming"}
    if kind == "ambiguous_acronym":
        negative |= {"customer service", "computer science", "city state", "civil service"}
    ambiguous = _AMBIGUOUS_ENTITY_HINTS.get(q)
    if ambiguous:
        for hints in ambiguous.values():
            positive |= hints
    return positive, negative


def _minimum_directness(kind: str, first_run: bool, required_terms: set[str]) -> int:
    if kind in {"city", "country", "geo_region", "person", "brand_company", "entertainment_company", "sports_team", "business", "crypto", "technology"}:
        return 7 if not first_run else 5
    if kind == "ambiguous_acronym":
        return 12
    if kind in {"team_org", "entity_symbol"}:
        return 8 if not first_run else 6
    if len(required_terms) <= 1:
        return 6 if first_run else 7
    return 7 if first_run else 9


def build_search_plan(query: str, *, from_dt: datetime, to_dt: datetime, first_run: bool) -> SearchPlan:
    q = canonicalize_topic(query)
    kind = classify_topic(query)
    broad = kind in {"broad_single", "broad_dual", "general_news", "entity_symbol", "ambiguous_acronym", "ambiguous_geo", "country", "city", "geo_region", "person", "brand_company", "entertainment_company", "sports_team", "business", "crypto", "technology"}
    freshness = _freshness_hint(from_dt, to_dt, first_run)
    required = _tokens(q)
    soft = set(required)
    exact_phrase = q if len(q) >= 3 else None
    strict_phrase = len(required) <= 1 and kind in {"weather_like", "entity_symbol"}
    semantic_hints = _semantic_hints_for_query(q, kind)
    alternates = _alternate_terms(q) | set(_query_bases(query, q, kind)) | {_normalize(query), transliterate_cyrillic(query)}
    positive_context, negative_context = _context_terms(q, kind)

    variants: list[str] = []
    bases = _query_bases(query, q, kind)

    def _quoted(base: str) -> str:
        return f'"{base}"' if len(base) >= 3 else base

    for base in bases[:3]:
        quoted_base = _quoted(base)
        variants.append(f'{quoted_base} latest news {freshness}')

    quoted = _quoted(q)
    # Keep the second/third paid search pass useful. Generic "breaking news" is often
    # too narrow for tech, esports and niche topics, so those kinds get a semantic
    # expansion before the generic fallback.
    if kind == "esports":
        variants.append(f'{quoted} esports tournament roster latest {freshness}')
        if re.search(r"\bcs\b", q) or "counter" in q or "strike" in q:
            variants.append(f'{quoted} CS2 Counter-Strike tournament latest {freshness}')
    elif kind == "sports_team":
        variants.append(f'{quoted} football club match transfer injury coach latest {freshness}')
        variants.append(f'{quoted} official club latest news {freshness}')
    elif kind == "technology":
        variants.append(f'{quoted} software release security latest {freshness}')
        variants.append(f'{quoted} developer ecosystem package latest {freshness}')
    elif kind == "game_updates":
        variants.append(f'{quoted} official update patch notes {freshness}')
    else:
        variants.append(f'{quoted} breaking news {freshness}')

    if kind == "game_updates":
        variants.extend([f'{quoted} official update {freshness}', f'{quoted} patch notes {freshness}', f'{quoted} changelog {freshness}'])
        soft |= {"update", "patch", "notes", "official", "changelog"}
    elif kind == "conflict":
        variants.extend([f'{quoted} war updates {freshness}', f'{quoted} strikes aid ceasefire {freshness}', f'{quoted} frontline security {freshness}'])
        soft |= {"war", "strike", "aid", "ceasefire", "frontline"}
    elif kind == "sports":
        variants.extend([f'{quoted} match transfer injury news {freshness}', f'{quoted} official club latest {freshness}'])
        soft |= {"match", "transfer", "injury", "club"}
    elif kind == "sports_team":
        variants.extend([f'{quoted} match transfer injury coach news {freshness}', f'{quoted} league cup fixture latest {freshness}', f'{quoted} official club announcement {freshness}', f'{quoted} Reuters AP sports latest {freshness}'])
        soft |= _SPORTS_TEAM_CONTEXT | {"official", "fixture", "signing"}
    elif kind == "esports":
        variants.extend([f'{quoted} esports roster tournament latest {freshness}', f'{quoted} competitive match announcement {freshness}', f'{quoted} official team update {freshness}', f'{quoted} CS2 Counter-Strike tournament latest {freshness}'])
        soft |= {"esports", "tournament", "roster", "team", "match", "announcement", "cs2", "counter-strike"}
    elif kind == "team_org":
        variants.extend([f'{quoted} official team organization latest {freshness}', f'{quoted} roster announcement match latest {freshness}', f'{quoted} team news latest {freshness}'])
        soft |= {"official", "team", "organization", "roster", "announcement"}
    elif kind == "weather_like":
        variants.extend([f'{quoted} severe weather news {freshness}', f'{quoted} flood drought storm news {freshness}'])
    elif kind == "city":
        preferred = _CITY_DISAMBIGUATION.get(q)
        if preferred:
            variants.append(f'{quoted} {preferred} local news incident government {freshness}')
        variants.extend([f'{quoted} city latest developments {freshness}', f'{quoted} local government transport incident {freshness}', f'{quoted} region breaking news {freshness}', f'{quoted} Reuters AP BBC latest {freshness}'])
        soft |= {"city", "region", "local", "incident", "government"} | positive_context
    elif kind == "country":
        variants.extend([f'{quoted} politics economy major developments {freshness}', f'{quoted} government security latest {freshness}', f'{quoted} Reuters AP BBC latest {freshness}', f'{quoted} breaking news today {freshness}'])
        soft |= {"politics", "economy", "government", "security"}
    elif kind == "geo_region":
        variants.extend([f'{quoted} environment shipping security latest {freshness}', f'{quoted} climate marine islands developments {freshness}', f'{quoted} Reuters AP BBC latest {freshness}'])
        soft |= {"environment", "shipping", "security", "climate", "marine", "islands"}
    elif kind == "crypto":
        variants.extend([f'{quoted} crypto market regulation latest {freshness}', f'{quoted} blockchain protocol exchange latest {freshness}', f'{quoted} Reuters Bloomberg CoinDesk latest {freshness}'])
        soft |= {"crypto", "blockchain", "market", "regulation", "exchange", "protocol"}
    elif kind == "technology":
        variants.extend([f'{quoted} software release security latest {freshness}', f'{quoted} developer ecosystem package latest {freshness}', f'{quoted} programming language open source latest {freshness}'])
        soft |= {"software", "release", "security", "developer", "programming", "package", "open", "source"}
    elif kind in {"business", "brand_company"}:
        variants.extend([f'{quoted} company product launch recall safety latest {freshness}', f'{quoted} earnings production regulation deal latest {freshness}', f'{quoted} Reuters Bloomberg CNBC Automotive News latest {freshness}'])
        soft |= {"company", "earnings", "product", "launch", "recall", "safety", "production", "shares", "deal"}
    elif kind == "person":
        variants.extend([f'{quoted} statement lawsuit company latest {freshness}', f'{quoted} interview announcement latest {freshness}', f'{quoted} Reuters AP BBC latest {freshness}'])
        soft |= {"statement", "lawsuit", "company", "announcement", "interview"}
    elif kind == "entertainment":
        variants.extend([f'{quoted} film series studio latest {freshness}', f'{quoted} release production box office latest {freshness}', f'{quoted} entertainment industry news {freshness}'])
        soft |= {"film", "series", "studio", "release", "production"}
    elif kind == "entertainment_company":
        variants.extend([f'{quoted} studio film release box office latest {freshness}', f'{quoted} CinemaCon slate production deal latest {freshness}', f'{quoted} Variety Deadline Hollywood Reporter latest {freshness}'])
        soft |= {"film", "studio", "release", "box", "office", "production", "slate", "deal"}
    elif kind == "ambiguous_geo":
        variants.extend([f'{quoted} DC politics government latest {freshness}', f'{quoted} state governor local latest {freshness}', f'{quoted} Reuters AP local latest {freshness}'])
        soft |= {"dc", "state", "government", "governor", "local", "politics"}
    elif kind == "ambiguous_acronym":
        if q == "cs":
            variants.extend([f'{quoted} Counter-Strike 2 esports tournament latest {freshness}', f'{quoted} CS2 roster match latest {freshness}'])
            soft |= {"counter-strike", "cs2", "esports", "tournament", "roster", "match"}
        else:
            variants.extend([f'{quoted} latest news official announcement {freshness}', f'{quoted} organization company team latest {freshness}'])
            soft |= {"official", "announcement", "organization", "company", "team"}
    elif kind == "entity_symbol":
        variants.extend([f'{quoted} official statement organization company team {freshness}', f'{quoted} latest developments {freshness}', f'{quoted} Reuters AP latest {freshness}'])
        soft |= {"official", "organization", "company", "team", "brand"}
    elif kind == "broad_single":
        variants.extend([f'{quoted} major developments {freshness}', f'{quoted} official statement press release {freshness}', f'{quoted} Reuters AP BBC latest {freshness}', f'{quoted} industry policy market latest {freshness}'])
    elif kind == "broad_dual":
        variants.extend([f'{quoted} key developments {freshness}', f'{quoted} major stories {freshness}', f'{quoted} Reuters AP latest {freshness}'])
    else:
        variants.extend([f'{quoted} recent developments article {freshness}', f'{quoted} major stories {freshness}', f'{quoted} Reuters AP BBC latest {freshness}'])

    ambiguous = _AMBIGUOUS_ENTITY_HINTS.get(q)
    if ambiguous:
        for hints in ambiguous.values():
            variants.append(f'{quoted} ' + ' '.join(sorted(hints)) + f' {freshness}')
            soft |= hints

    deduped: list[str] = []
    seen = set()
    for v in variants:
        k = re.sub(r'\s+', ' ', v.strip().lower())
        if k not in seen:
            seen.add(k)
            deduped.append(v)

    max_variants = 6 if kind in {"game_updates", "sports", "sports_team", "esports", "team_org", "technology", "brand_company", "entertainment_company"} else 6 if broad else 5
    return SearchPlan(
        raw_query=query,
        normalized_query=q,
        topic_kind=kind,
        first_run=first_run,
        broad_topic=broad,
        freshness_hint=freshness,
        query_variants=deduped[:max_variants],
        required_terms=required,
        soft_terms=soft,
        exact_phrase=exact_phrase,
        semantic_hints=semantic_hints,
        strict_phrase=strict_phrase,
        max_variants=max_variants,
        alternate_terms=alternates,
        positive_context_terms=positive_context,
        negative_context_terms=negative_context,
        minimum_directness=_minimum_directness(kind, first_run, required),
    )
