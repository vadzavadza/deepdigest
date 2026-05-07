from __future__ import annotations

from urllib.parse import urlparse


def normalize_source_name(source_name: str | None) -> str:
    value = (source_name or "").lower().strip().replace("www.", "")
    if value.startswith("http://") or value.startswith("https://"):
        value = urlparse(value).netloc.lower().replace("www.", "")
    return value


_GLOBAL_TIER1 = (
    "reuters", "apnews", "associated press", "bbc", "bloomberg", "ft.com", "financial times",
    "wsj", "wall street journal", "cnbc", "guardian", "nytimes", "new york times", "sky news",
    "dw.com", "cbsnews", "abcnews", "nbcnews", "npr", "politico", "axios",
)

_ALWAYS_BLOCKED = (
    "youtube", "youtu.be", "wikipedia", "wikimedia", "reddit", "facebook", "instagram", "tiktok",
    "iheart", "pinterest", "quora",
)

_FINANCE_SOURCES = (
    "marketbeat", "stockanalysis", "tradingview", "investorplace", "zacks", "motleyfool",
    "financeoutlookindia", "economic times", "economictimes", "moneycontrol", "inforcapital",
)

_WEAK_GENERAL_SOURCES = (
    "antigua.news", "newsminimalist", "tourprom", "eadaily", "kp.ru", "u.today", "weex",
    "coinmarketcap", "cryptonews", "stocktradersdaily", "vashon-maury", "vashonnews",
)

_VERTICAL_STRONG: dict[str, tuple[str, ...]] = {
    "sports_team": (
        "espn", "theathletic", "the athletic", "skysports", "sky sports", "bbc sport", "marca",
        "as.com", "football-espana", "onefootball", "goal.com", "eurosport", "cbssports",
    ),
    "sports": (
        "espn", "theathletic", "the athletic", "skysports", "sky sports", "bbc sport", "marca",
        "as.com", "goal.com", "eurosport", "cbssports",
    ),
    "team_org": (
        "hltv", "dust2", "esports.gg", "esportsinsider", "bo3.gg", "talkesport", "liquipedia",
        "vlr.gg", "dotesports", "dexerto", "gosugamers",
    ),
    "esports": (
        "hltv", "dust2", "esports.gg", "esportsinsider", "bo3.gg", "talkesport", "liquipedia",
        "vlr.gg", "dotesports", "dexerto", "gosugamers",
    ),
    "brand_company": (
        "automotivenews", "automotive news", "carscoops", "motor1", "autoblog", "caranddriver",
        "topgear", "nhtsa", "pressroom", "media.toyota", "toyota.com", "lexus", "audi.com",
        "microsoft.com", "apple.com", "openai.com", "techcrunch", "theverge", "wired",
    ),
    "business": (
        "reuters", "bloomberg", "cnbc", "ft.com", "financial times", "wsj", "wall street journal",
        "marketwatch", "seekingalpha", "businesswire", "prnewswire",
    ),
    "crypto": (
        "coindesk", "cointelegraph", "theblock", "decrypt", "cryptoslate", "bitcoinmagazine", "blockworks",
        "reuters", "bloomberg",
    ),
    "entertainment_company": (
        "variety", "deadline", "hollywoodreporter", "hollywood reporter", "thewrap", "screendaily",
        "boxoffice", "indiewire", "screenrant",
    ),
    "entertainment": (
        "variety", "deadline", "hollywoodreporter", "hollywood reporter", "thewrap", "screendaily",
        "indiewire", "billboard", "rollingstone",
    ),
    "technology": (
        "techcrunch", "theverge", "wired", "arstechnica", "zdnet", "bleepingcomputer", "theregister",
        "github", "python.org", "microsoft.com", "googleblog", "openai.com",
    ),
    "city": (
        "apnews", "reuters", "bbc", "dw.com", "theguardian", "nytimes", "cbsnews", "abcnews",
        "nbcnews", "local", "city", "gov",
    ),
    "country": (
        "apnews", "reuters", "bbc", "dw.com", "theguardian", "nytimes", "cbsnews", "abcnews",
        "nbcnews", "politico", "axios",
    ),
}

_VERTICAL_HARD_MISMATCH: dict[str, tuple[str, ...]] = {
    "team_org": _FINANCE_SOURCES + ("constructiontechnology", "therealtytoday", "phemex", "medial.app"),
    "esports": _FINANCE_SOURCES + ("constructiontechnology", "therealtytoday", "phemex", "medial.app"),
    "sports_team": _FINANCE_SOURCES + ("constructiontechnology", "therealtytoday", "phemex", "medial.app"),
    "sports": _FINANCE_SOURCES + ("constructiontechnology", "therealtytoday", "phemex", "medial.app"),
    "entertainment_company": _FINANCE_SOURCES + ("coinmarketcap", "weex", "phemex"),
    "crypto": ("caranddriver", "carscoops", "motor1", "autoblog", "goal.com", "espn"),
}


def _contains_any(value: str, needles: tuple[str, ...]) -> bool:
    return any(n in value for n in needles)


def source_vertical_mismatch(source_name: str | None, topic_kind: str | None) -> bool:
    normalized = normalize_source_name(source_name)
    kind = (topic_kind or "").lower()
    if _contains_any(normalized, _ALWAYS_BLOCKED):
        return True
    hard = _VERTICAL_HARD_MISMATCH.get(kind, ())
    return _contains_any(normalized, hard)


def source_quality_weight(source_name: str | None, topic_kind: str | None = None) -> float:
    normalized = normalize_source_name(source_name)
    kind = (topic_kind or "").lower()
    if not normalized:
        return 0.0
    if _contains_any(normalized, _ALWAYS_BLOCKED):
        return -120.0
    if source_vertical_mismatch(normalized, kind):
        return -60.0

    base = 8.0
    if _contains_any(normalized, _GLOBAL_TIER1):
        base = 30.0
    elif _contains_any(normalized, _WEAK_GENERAL_SOURCES):
        base = -14.0
    elif _contains_any(normalized, _FINANCE_SOURCES):
        base = 6.0 if kind in {"business", "brand_company"} else -24.0
    elif "prnewswire" in normalized or "businesswire" in normalized:
        base = 5.0

    strong_for_kind = _VERTICAL_STRONG.get(kind, ())
    if strong_for_kind and _contains_any(normalized, strong_for_kind):
        base += 16.0

    # Vertical-specific weak-source penalties. These are not topic-specific; they prevent
    # finance/SEO/aggregator pages from winning unrelated digests.
    if kind == "brand_company":
        if _contains_any(normalized, ("marketbeat", "antigua.news", "torquenews", "techradar", "tomsguide")):
            base -= 14.0
        if _contains_any(normalized, ("pressroom", "official", "media.toyota", "toyota.com", "audi.com", "lexus")):
            base += 10.0
    elif kind in {"team_org", "esports", "sports", "sports_team"}:
        if _contains_any(normalized, _FINANCE_SOURCES + ("finance", "stock", "market")):
            base -= 40.0
    elif kind == "entertainment_company":
        if _contains_any(normalized, ("newsminimalist", "awardsradar")):
            base -= 10.0
    elif kind == "crypto":
        if _contains_any(normalized, ("weex", "coinmarketcap", "u.today")):
            base -= 14.0

    return base


def source_authority_tier(source_name: str | None, topic_kind: str | None = None) -> str:
    weight = source_quality_weight(source_name, topic_kind)
    if weight >= 28:
        return "tier1"
    if weight >= 16:
        return "strong_niche"
    if weight >= 8:
        return "standard"
    if weight >= 0:
        return "weak_usable"
    if weight <= -50:
        return "blocked_mismatch"
    return "weak"


def weak_source_allowed(source_name: str | None, topic_kind: str | None = None) -> bool:
    return source_quality_weight(source_name, topic_kind) >= 0 and not source_vertical_mismatch(source_name, topic_kind)
