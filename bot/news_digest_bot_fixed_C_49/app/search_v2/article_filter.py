from __future__ import annotations

from dataclasses import dataclass
import html
import re
from urllib.parse import urlparse

from .strategy import SearchPlan

_SECTION_PATTERNS = (
    "/all", "/latest", "/latest-news", "/archive", "/archives", "/tag/", "/tags/", "/topic/", "/topics/", "/category/",
    "/categories/", "/section/", "/sections/", "/topics-and-tag/", "/search", "/sitemap"
)
_BAD_TITLE_HINTS = {
    "category:", "tag:", "all |", "latest |", "watch", "video", "podcast", "newsletter", "live blog", "live updates",
    "latest news", "news today", "latest headlines", "transfer rumours", "transfer rumors", "team news", "news hub"
}
_STOPWORDS = {
    "the","a","an","and","or","of","in","on","to","for","de","la","el","en","y","los","las","le","un","una",
    "se","es","are","is","latest","news","update","updates","recent","today","yesterday","city","breaking"
}
_FINANCE_ONLY_HINTS = {"stock", "shares", "nasdaq", "nyse", "price target", "momentum shifts", "$", "investorplace", "motley fool", "zacks"}
_SPORTS_ONLY_HINTS = {"transfer", "rumours", "rumors", "lineup", "goal.com"}
_TEAM_GENERIC_DRIFT_HINTS = {"team spirit key to", "copa américa", "copa america", "locker room", "chemistry", "spirit key", "strong team spirit"}
_BUSINESS_HINTS = {"earnings", "shares", "stock", "market", "results", "guidance", "investor", "ceo"}
_EVERGREEN_HINTS = {
    "things to do", "what to do", "where to stay", "travel guide", "best restaurants", "best hotels", "tourist guide",
    "weather spark", "average weather", "monthly weather", "hourly forecast", "10-day forecast", "calendar of events",
    "tickets", "how to watch", "wiki", "explained:", "guide to", "complete guide", "preview and prediction"
}
_REVIEW_BUYING_HINTS = {
    "review:", " review", "hands-on", "hands on", "i drove", "we drove", "for a week", "buyers guide", "buying guide",
    "best cars", "best suvs", "pros and cons", "should you buy", "here's what", "here is what", "what you need to know"
}
_AMBIGUOUS_CS_CONTEXT = {"counter-strike", "counter strike", "cs2", "esports", "hltv", "blast", "iem", "esl", "valve", "major", "tournament", "roster"}
_SERVICE_PAGE_HINTS = {
    "homepage", "login", "subscribe", "sign up", "newsletter", "contact us", "privacy policy", "terms of service",
    "customer faq", "faq", "help center", "support page", "learn how", "how to", "troubleshooting",
}


@dataclass(slots=True)
class HtmlMetadata:
    title: str | None
    description: str | None
    canonical_url: str | None
    language: str | None


@dataclass(slots=True)
class CandidateQuality:
    accepted: bool
    score: int
    directness_score: int
    reason: str | None
    features: dict[str, int | bool]


def extract_html_metadata(html_text: str) -> HtmlMetadata:
    title = None
    desc = None
    canonical = None
    lang = None
    patterns = [
        (r'''<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']''', "title"),
        (r'''<title>([^<]+)</title>''', "title"),
        (r'''<meta[^>]+name=["']description["'][^>]+content=["']([^"']+)["']''', "desc"),
        (r'''<meta[^>]+property=["']og:description["'][^>]+content=["']([^"']+)["']''', "desc"),
        (r'''<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']''', "canonical"),
        (r'''<html[^>]+lang=["']([a-zA-Z-]+)["']''', "lang"),
    ]
    for pattern, kind in patterns:
        m = re.search(pattern, html_text, re.IGNORECASE)
        if not m:
            continue
        value = html.unescape(m.group(1).strip())
        if kind == "title" and title is None:
            title = value
        elif kind == "desc" and desc is None:
            desc = value
        elif kind == "canonical" and canonical is None:
            canonical = value
        elif kind == "lang" and lang is None:
            lang = value.split("-")[0].lower()
    return HtmlMetadata(title=title, description=desc, canonical_url=canonical, language=lang)


def _meaningful_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9а-яА-ЯёЁіІїЇєЄґҐ]+", text.lower()) if len(t) >= 3 and t not in _STOPWORDS}


def _multiword_alt_hit(plan: SearchPlan, hay_l: str) -> int:
    hits = 0
    for alt in plan.alternate_terms or set():
        alt_l = alt.lower()
        if len(alt_l) >= 3 and alt_l in hay_l:
            hits += 1
    return hits


def topic_match_features(plan: SearchPlan, *, title: str | None, description: str | None, url: str) -> dict[str, int | bool]:
    title_text = title or ""
    desc_text = description or ""
    path_text = urlparse(url).path.replace("-", " ").replace("_", " ").replace("/", " ")
    hay = " ".join(x for x in [title_text, desc_text, path_text] if x)
    hay_l = hay.lower()
    title_tokens = _meaningful_tokens(title_text)
    desc_tokens = _meaningful_tokens(desc_text)
    path_tokens = _meaningful_tokens(path_text)
    all_tokens = _meaningful_tokens(hay)
    required_hits = len(all_tokens & plan.required_terms)
    title_hits = len(title_tokens & plan.required_terms)
    desc_hits = len(desc_tokens & plan.required_terms)
    path_hits = len(path_tokens & plan.required_terms)
    semantic_hits = len(all_tokens & plan.semantic_hints)
    alt_token_hits = len(all_tokens & (plan.alternate_terms or set()))
    alt_phrase_hits = _multiword_alt_hit(plan, hay_l)
    exact_phrase = bool(plan.exact_phrase and plan.exact_phrase in hay_l)
    positive_context_hits = sum(1 for term in plan.positive_context_terms if term.lower() in hay_l)
    negative_context_hits = sum(1 for term in plan.negative_context_terms if term.lower() in hay_l)
    return {
        "required_hits": required_hits,
        "title_hits": title_hits,
        "desc_hits": desc_hits,
        "path_hits": path_hits,
        "semantic_hits": semantic_hits,
        "alternate_hits": alt_token_hits + alt_phrase_hits,
        "exact_phrase": exact_phrase,
        "positive_context_hits": positive_context_hits,
        "negative_context_hits": negative_context_hits,
    }


def topic_match_score(plan: SearchPlan, *, title: str | None, description: str | None, url: str) -> int:
    f = topic_match_features(plan, title=title, description=description, url=url)
    score = (
        int(f["required_hits"]) * 5
        + int(f["title_hits"]) * 5
        + int(f["desc_hits"]) * 2
        + int(f["semantic_hits"]) * 2
        + int(f["alternate_hits"]) * 4
        + int(f["positive_context_hits"]) * 4
    )
    if f["exact_phrase"]:
        score += 10
    if int(f["negative_context_hits"]) > 0:
        score -= 10 * int(f["negative_context_hits"])
    return score


def directness_score(plan: SearchPlan, *, title: str | None, description: str | None, url: str) -> int:
    f = topic_match_features(plan, title=title, description=description, url=url)
    score = (
        int(f["title_hits"]) * 8
        + int(f["desc_hits"]) * 3
        + int(f["alternate_hits"]) * 5
        + int(f["semantic_hits"]) * 1
        + int(f["positive_context_hits"]) * 3
    )
    if f["exact_phrase"]:
        score += 12
    if int(f["required_hits"]) > 0 and (int(f["title_hits"]) > 0 or int(f["desc_hits"]) > 0):
        score += 4
    if int(f["path_hits"]) > 0 and int(f["title_hits"]) == 0 and int(f["desc_hits"]) == 0:
        score -= 4
    score -= 12 * int(f["negative_context_hits"])
    return score


def _contains_any(haystack: str, needles: set[str]) -> bool:
    return any(n in haystack for n in needles)


def _looks_like_topic_news_hub(plan: SearchPlan, *, title: str | None, url: str) -> bool:
    if not title:
        return False
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip("/")
    title_norm = re.sub(r"\s+", " ", title.lower()).strip()
    q = re.escape(plan.normalized_query.lower())
    # Examples: "Microsoft News | Windows Central", "Bitcoin News Today", "Trump latest news".
    if re.match(rf"^{q}\s+(latest\s+)?news(\s*(today|and|&|\||-|–|—|:)|$)", title_norm):
        return True
    if re.match(rf"^latest\s+{q}\s+news(\s*(today|and|&|\||-|–|—|:)|$)", title_norm):
        return True
    short_hub_paths = {"", "/news", "/latest", "/latest-news", "/world", "/business", "/politics", "/markets", "/sport", "/sports", "/technology", "/tech"}
    if path in short_hub_paths and " news" in title_norm and plan.normalized_query.lower() in title_norm:
        return True
    return False


def rejection_reason(plan: SearchPlan, *, url: str, title: str | None, description: str | None) -> str | None:
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip("/")
    title_norm = (title or "").lower()
    host = parsed.netloc.lower()
    desc_norm = (description or "").lower()
    hay = f"{title_norm} {desc_norm} {host} {path}"

    if not parsed.scheme.startswith("http") or not host:
        return "invalid_url"
    if any(p in path for p in _SECTION_PATTERNS):
        return "section_or_index_page"
    if any(h in title_norm for h in _BAD_TITLE_HINTS):
        return "bad_title_hint"
    if _looks_like_topic_news_hub(plan, title=title, url=url):
        return "topic_news_hub_page"
    if any(seg in path for seg in ("/live/", "/live-blog", "/liveblog", "/video/", "/videos/", "/watch", "/podcast", "/audio/", "/gallery/")):
        return "non_article_media_or_live_page"
    shallow = path.count("/") < 2 or path in {"/news", "/latest-news", "/latest", "/world", "/sport", "/sports", "/politics", "/business", "/markets"}
    if shallow and not re.search(r"/20\d{2}/", path) and len(path) < 30:
        return "shallow_non_article_url"
    if shallow and ("latest news" in title_norm or "news today" in title_norm or "headlines" in title_norm):
        return "news_hub_page"
    if "| the guardian" in title_norm and (path.endswith("/all") or path.endswith("/latest")):
        return "section_or_index_page"

    if plan.topic_kind != "weather_like" and _contains_any(hay, _EVERGREEN_HINTS):
        return "evergreen_or_service_content"
    if plan.topic_kind in {"brand_company", "business", "technology"} and _contains_any(hay, _REVIEW_BUYING_HINTS):
        return "review_or_buying_guide"
    if _contains_any(hay, _SERVICE_PAGE_HINTS):
        return "evergreen_or_service_content"
    if plan.topic_kind in {"brand_company", "technology"}:
        service_path = any(seg in path for seg in ("/support", "/faq", "/help", "/customer-service", "/learn", "/manual"))
        newsroom_path = any(seg in path for seg in ("/news", "/press", "/media", "/newsroom", "/stories", "/story"))
        if service_path and not newsroom_path:
            return "evergreen_or_service_content"

    features = topic_match_features(plan, title=title, description=description, url=url)
    required_hits = int(features["required_hits"])
    title_hits = int(features["title_hits"])
    desc_hits = int(features["desc_hits"])
    semantic_hits = int(features["semantic_hits"])
    alt_hits = int(features["alternate_hits"])
    positive_context_hits = int(features["positive_context_hits"])
    negative_context_hits = int(features["negative_context_hits"])

    if negative_context_hits > 0 and positive_context_hits == 0 and semantic_hits == 0:
        return "wrong_entity_context"
    if plan.topic_kind == "ambiguous_acronym":
        if plan.normalized_query == "cs" and not any(marker in hay for marker in _AMBIGUOUS_CS_CONTEXT):
            return "ambiguous_acronym_without_context"
        if title_hits == 0 and desc_hits == 0 and alt_hits == 0 and not bool(features["exact_phrase"]):
            return "ambiguous_acronym_without_context"

    if plan.strict_phrase and not (bool(features["exact_phrase"]) or title_hits > 0 or desc_hits > 0 or alt_hits > 0):
        return "missing_strict_phrase"
    if plan.topic_kind == "conflict" and semantic_hits == 0 and not bool(features["exact_phrase"]) and title_hits == 0:
        return "low_conflict_directness"

    if plan.topic_kind in {"entity_symbol", "team_org"} and any(h in hay for h in _FINANCE_ONLY_HINTS) and not any(h in plan.normalized_query for h in _BUSINESS_HINTS):
        return "finance_only_drift"
    if plan.topic_kind == "city" and any(h in title_norm for h in _SPORTS_ONLY_HINTS) and "fc" not in plan.normalized_query:
        return "sports_drift_for_city"
    if plan.topic_kind == "team_org":
        if any(h in hay for h in _TEAM_GENERIC_DRIFT_HINTS):
            return "generic_phrase_not_entity"
        # v6: do not require the exact user phrase when it contains generic words
        # like "team". Articles often say "NAVI" or "Natus Vincere" rather than
        # "NAVI TEAM". Strong title/alternate/direct hits are enough.
        if (
            plan.exact_phrase
            and plan.exact_phrase not in hay
            and len(plan.required_terms) >= 2
            and title_hits == 0
            and desc_hits == 0
            and alt_hits == 0
            and semantic_hits == 0
        ):
            return "missing_team_phrase"

    score = topic_match_score(plan, title=title, description=description, url=url)
    direct = directness_score(plan, title=title, description=description, url=url)
    threshold = 4 if plan.first_run and plan.broad_topic else 6
    if plan.topic_kind in {"city", "country"}:
        threshold = 3 if plan.first_run else 5
    if score < threshold:
        return "topic_score_below_threshold"
    if (
        plan.topic_kind in {"country", "city", "geo_region", "person", "business", "crypto", "technology"}
        and title_hits == 0
        and semantic_hits == 0
        and alt_hits == 0
        and not bool(features["exact_phrase"])
    ):
        return "indirect_relevance"
    if direct < plan.minimum_directness:
        return "low_directness"

    if required_hits == 0 and alt_hits == 0 and not bool(features["exact_phrase"]) and semantic_hits > 0 and title_hits == 0 and desc_hits == 0:
        return "semantic_only_match"
    if title_hits == 0 and required_hits == 0 and alt_hits == 0 and len(_meaningful_tokens(desc_norm)) < 5:
        return "no_direct_topic_evidence"
    if article_confidence(url, title, description) < 1:
        return "low_article_confidence"
    return None


def candidate_quality(plan: SearchPlan, *, url: str, title: str | None, description: str | None) -> CandidateQuality:
    features = topic_match_features(plan, title=title, description=description, url=url)
    score = topic_match_score(plan, title=title, description=description, url=url)
    direct = directness_score(plan, title=title, description=description, url=url)
    reason = rejection_reason(plan, url=url, title=title, description=description)
    return CandidateQuality(
        accepted=reason is None,
        score=score,
        directness_score=direct,
        reason=reason,
        features=features,
    )


def is_candidate_article(plan: SearchPlan, *, url: str, title: str | None, description: str | None) -> bool:
    return candidate_quality(plan, url=url, title=title, description=description).accepted


def article_confidence(url: str, title: str | None, description: str | None) -> int:
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip('/')
    title_norm = (title or '').lower()
    desc_norm = (description or '').lower()
    score = 0
    if re.search(r'/20\d{2}/', path):
        score += 5
    if path in {"/news", "/latest-news", "/latest", "/world", "/sport", "/sports", "/politics", "/business", "/markets"}:
        score -= 6
    if any(seg in path for seg in ('/news', '/article', '/articles', '/story', '/stories', '/world', '/business', '/politics', '/technology', '/sport', '/sports')):
        score += 4
    if any(seg in path for seg in ('/video', '/videos', '/watch', '/podcast', '/tag/', '/topic/', '/topics/', '/category/', '/categories/', '/archive', '/archives', '/all', '/latest')):
        score -= 8
    if title_norm and len(_meaningful_tokens(title_norm)) >= 3:
        score += 2
    if desc_norm and len(_meaningful_tokens(desc_norm)) >= 4:
        score += 1
    if 'latest news' in title_norm or 'news today' in title_norm or 'headlines' in title_norm:
        score -= 4
    if title_norm.endswith(" news") or " news |" in title_norm or " news -" in title_norm:
        score -= 5
    if any(h in f"{title_norm} {desc_norm} {path}" for h in _EVERGREEN_HINTS):
        score -= 4
    return score
