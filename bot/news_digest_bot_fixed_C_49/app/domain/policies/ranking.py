from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.schemas.sources import NormalizedSourceItem, StoryCandidate

_LANGUAGE_PRIORITY = {
    "en": 100.0,
    "de": 90.0,
    "uk": 82.0,
    "ru": 40.0,
}

_SOURCE_QUALITY = {
    "reuters": 36.0,
    "ap": 34.0,
    "associated press": 34.0,
    "apnews.com": 34.0,
    "bloomberg": 22.0,
    "financial times": 31.0,
    "ft": 31.0,
    "wsj": 30.0,
    "wall street journal": 30.0,
    "bbc": 28.0,
    "dw": 27.0,
    "the independent": 14.0,
    "handelsblatt": 27.0,
    "cnn": 24.0,
    "cnbc": 23.0,
    "sky news": 22.0,
    "the guardian": 24.0,
    "guardian": 24.0,
    "new york times": 26.0,
    "nyt": 26.0,
    "le monde": 21.0,
    "fox business": 8.0,
    "foxnews": 6.0,
    "motley fool": -8.0,
    "investorplace": -18.0,
    "zacks": -14.0,
    "stock traders daily": -25.0,
    "goal.com": 4.0,
    "bo3.gg": 3.0,
    "csgo.com": 8.0,
    "hltv.org": 16.0,
    "liquipedia.net": 5.0,
    "flashscore": -10.0,
    "esports.net": -4.0,
    "vsau.com": -6.0,
    "english.news.cn": -6.0,
    "youtube": -120.0,
    "iheart": -90.0,
    "reddit": -90.0,
    "wikipedia": -120.0,
    "wikimedia": -120.0,
}

_TRUSTED_HOST_SNIPPETS = ("reuters", "apnews", "bbc", "dw", "ft.com", "wsj", "theguardian", "nytimes", "cnn", "cnbc")
_WEAK_HOST_SNIPPETS = ("motleyfool", "investorplace", "zacks", "stocktradersdaily", "news.cn", "flashscore", "vsau", "esports.net", "bo3.gg", "weex", "cryptonews", "u.today", "coinmarketcap", "tourprom", "eadaily", "kp.ru")


def language_priority(language: str | None) -> float:
    if language is None:
        return 60.0
    return _LANGUAGE_PRIORITY.get(language.lower(), 60.0)


def _normalize_source_name(source_name: str) -> str:
    return source_name.lower().replace('www.', '').strip()


def _vertical_source_adjustment(normalized: str, topic_kind: str | None) -> float:
    kind = (topic_kind or "").lower()
    if kind in {"sports", "sports_team"}:
        if any(x in normalized for x in ("espn", "theathletic", "the athletic", "skysports", "sky sports", "bbc sport", "marca", "as.com", "football-espana", "onefootball")):
            return 14.0
        if "fichajes" in normalized or "fourfourtwo" in normalized:
            return 4.0
    if kind in {"brand_company", "business"}:
        if any(x in normalized for x in ("automotivenews", "automotive news", "carscoops", "motor1", "autoblog", "caranddriver", "topgear", "nhtsa", "carsguide")):
            return 8.0
        if any(x in normalized for x in ("tomsguide", "techradar")):
            return -10.0
    if kind == "entertainment_company":
        if any(x in normalized for x in ("variety", "deadline", "hollywoodreporter", "hollywood reporter", "thewrap", "screendaily", "boxoffice")):
            return 18.0
        if "awardsradar" in normalized:
            return 2.0
        if "newsminimalist" in normalized:
            return -14.0
    if kind == "crypto":
        if any(x in normalized for x in ("coindesk", "cointelegraph", "theblock", "decrypt", "cryptoslate")):
            return 8.0
        if any(x in normalized for x in ("weex", "coinmarketcap")):
            return -16.0
    return 0.0


def source_quality_weight(source_name: str, topic_kind: str | None = None) -> float:
    normalized = _normalize_source_name(source_name)
    base: float
    if normalized in _SOURCE_QUALITY:
        base = _SOURCE_QUALITY[normalized]
    elif 'youtube' in normalized or 'youtu.be' in normalized:
        base = -120.0
    elif 'wikipedia' in normalized or 'wikimedia' in normalized:
        base = -120.0
    elif 'iheart' in normalized or 'reddit' in normalized:
        base = -90.0
    elif 'reuters' in normalized:
        base = 36.0
    elif 'associated press' in normalized or normalized == 'ap' or 'apnews' in normalized:
        base = 34.0
    elif 'bloomberg' in normalized:
        base = 22.0
    elif 'ft.com' in normalized or 'financial times' in normalized:
        base = 31.0
    elif 'wsj' in normalized or 'wall street journal' in normalized:
        base = 30.0
    elif 'bbc' in normalized:
        base = 28.0
    elif 'dw.com' in normalized or normalized == 'dw':
        base = 27.0
    elif 'sky.com' in normalized or 'sky news' in normalized:
        base = 24.0
    elif 'guardian' in normalized:
        base = 24.0
    elif 'nytimes' in normalized or normalized == 'nyt':
        base = 26.0
    elif 'weex' in normalized:
        base = -24.0
    elif 'coinmarketcap' in normalized:
        base = -10.0
    elif 'cryptobriefing' in normalized or 'news.bitcoin' in normalized:
        base = 6.0
    elif 'carscoops' in normalized or 'autoblog' in normalized or 'motor1' in normalized:
        base = 9.0
    elif 'newsminimalist' in normalized:
        base = -8.0
    elif 'tourprom' in normalized or 'eadaily' in normalized or 'kp.ru' in normalized:
        base = -12.0
    elif 'motleyfool' in normalized:
        base = -8.0
    elif 'investorplace' in normalized or 'zacks' in normalized or 'stocktradersdaily' in normalized:
        base = -18.0
    elif 'bo3.gg' in normalized:
        base = 3.0
    elif 'csgo.com' in normalized:
        base = 8.0
    elif 'hltv' in normalized:
        base = 16.0
    elif 'liquipedia' in normalized:
        base = 5.0
    elif 'flashscore' in normalized:
        base = -10.0
    elif 'esports.net' in normalized:
        base = -4.0
    elif 'vsau' in normalized:
        base = -6.0
    elif 'english.news.cn' in normalized or normalized.endswith('news.cn'):
        base = -6.0
    elif any(s in normalized for s in _TRUSTED_HOST_SNIPPETS):
        base = 22.0
    elif any(s in normalized for s in _WEAK_HOST_SNIPPETS):
        base = -6.0
    else:
        base = 10.0
    return base + _vertical_source_adjustment(normalized, topic_kind)


def source_authority_tier(source_name: str, topic_kind: str | None = None) -> str:
    weight = source_quality_weight(source_name, topic_kind)
    if weight >= 22.0:
        return "strong"
    if weight >= 8.0:
        return "standard"
    if weight >= 0.0:
        return "niche"
    return "weak"

def freshness_weight(published_at: datetime) -> float:
    now = datetime.now(tz=timezone.utc)
    delta_hours = max((now - published_at).total_seconds() / 3600.0, 0.0)
    return max(0.0, 24.0 - min(delta_hours, 24.0))


def freshness_confidence_penalty(article: NormalizedSourceItem) -> float:
    source = str(article.metadata.get("published_at_source", ""))
    if article.metadata.get("freshness_verified") is False:
        if source == "search_snippet":
            return -18.0
        return -24.0
    if source == "last_modified":
        return -12.0
    return 0.0


def url_quality_penalty(article: NormalizedSourceItem) -> float:
    raw = str(article.url or "")
    path = urlparse(raw).path.lower()
    title = article.title.lower()
    penalty = 0.0
    if any(seg in path for seg in ("/all", "/latest", "/tag/", "/topic/", "/category/", "/video/", "/watch")):
        penalty -= 20.0
    if "latest news" in title or "news today" in title or "headlines" in title or "team news" in title:
        penalty -= 12.0
    return penalty


def article_score(article: NormalizedSourceItem) -> float:
    return (
        freshness_weight(article.published_at)
        + source_quality_weight(article.source_name, str(article.metadata.get("topic_kind", "")))
        + language_priority(article.source_language)
        + float(article.metadata.get("topic_match_score", 0)) * 1.0
        + float(article.metadata.get("directness_score", 0)) * 1.8
        + float(article.metadata.get("article_confidence", 0)) * 2.0
        + url_quality_penalty(article)
        + freshness_confidence_penalty(article)
    )


def select_primary_article(candidates: list[NormalizedSourceItem]) -> NormalizedSourceItem:
    return max(
        candidates,
        key=lambda article: (
            article_score(article),
            article.published_at,
            len(article.title),
            str(article.url or ""),
        ),
    )


def story_score(story: StoryCandidate) -> float:
    primary = select_primary_article(story.articles)
    source_diversity_bonus = min(len({article.source_name for article in story.articles}), 3)
    language = (primary.source_language or "").lower()
    language_bonus = 6.0 if language == "en" else 4.0 if language in {"de", "uk"} else 0.0
    recency_bonus = freshness_weight(primary.published_at) * 0.25
    directness_bonus = max(float(article.metadata.get("directness_score", 0)) for article in story.articles) * 0.7
    return article_score(primary) + float(len(story.articles)) + source_diversity_bonus + language_bonus + recency_bonus + directness_bonus



def _source_key(article: NormalizedSourceItem) -> str:
    raw = str(article.url or '')
    host = urlparse(raw).netloc.lower().replace('www.', '')
    return host or _normalize_source_name(article.source_name)


def select_diverse_stories(candidates: Iterable[StoryCandidate], limit: int) -> list[StoryCandidate]:
    """Select stories in stages: first unique domains, then repeat domains only if needed.

    A soft penalty is not enough for small digests: one strong source can otherwise take
    several slots. This keeps the first pass diverse while still allowing a second item
    from the same domain when there are not enough good alternatives.
    """
    ordered = rank_stories(candidates)
    if limit <= 0:
        return []

    selected: list[StoryCandidate] = []
    used_sources: set[str] = set()

    # Pass 1: best stories from unique domains.
    for story in ordered:
        primary = select_primary_article(story.articles)
        source_key = _source_key(primary)
        if source_key in used_sources:
            continue
        selected.append(story)
        used_sources.add(source_key)
        if len(selected) >= limit:
            return selected

    # Pass 2: fill remaining slots, allowing repeats but still preserving ranking.
    selected_hashes = {story.story_hash for story in selected}
    for story in ordered:
        if story.story_hash in selected_hashes:
            continue
        selected.append(story)
        selected_hashes.add(story.story_hash)
        if len(selected) >= limit:
            return selected

    return selected

def rank_stories(candidates: Iterable[StoryCandidate]) -> list[StoryCandidate]:
    return sorted(
        candidates,
        key=lambda story: (
            story_score(story),
            select_primary_article(story.articles).published_at,
            story.story_hash,
        ),
        reverse=True,
    )

# v7 override: shared editorial source-quality model.
from app.search_v2.source_quality import (  # noqa: E402,F811
    source_quality_weight as source_quality_weight,
    source_authority_tier as source_authority_tier,
    source_vertical_mismatch as source_vertical_mismatch,
)
