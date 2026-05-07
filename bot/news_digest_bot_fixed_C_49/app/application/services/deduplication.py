from __future__ import annotations

from collections import defaultdict
import re
from hashlib import sha256
from urllib.parse import urlparse

from rapidfuzz import fuzz

from app.domain.enums import SourceType
from app.domain.policies.normalization import live_prefix, normalize_title
from app.schemas.articles import RawArticle
from app.schemas.sources import NormalizedSourceItem, RawSourceItem, StoryCandidate

_EXCLUDED_HOST_SNIPPETS = (
    'wikipedia.org',
    'wikimedia.org',
    'wikinews.org',
    'youtube.com',
    'youtu.be',
    'iheart.com',
    'reddit.com',
    'facebook.com',
    'instagram.com',
    'tiktok.com',
)

_STOPWORDS = {
    "the","a","an","and","or","of","in","on","to","for","de","la","el","en","y","los","las","le","un","una",
    "se","es","are","is","latest","news","update","updates","new","today","breaking",
    "в","у","і","й","та","на","з","за","до","про","як","що","це","від","для","над","під","при","із","зі",
    "и","а","но","или","по","из","от","для","над","под","при","это","как","что","об",
}
_MODEL_HINTS = {"bmw","series","i7","7","facelift","neue","klasse","cs2","patch","update","ukraine","war","usa","us","apple","iphone","ipad","mac"}
_EVENT_TERMS = {
    "match", "game", "beat", "beats", "defeat", "defeats", "win", "wins", "victory", "penalty", "league", "round",
    "матч", "матчі", "матчу", "переміг", "перемога", "переможе", "пенальті", "ліга", "лізі", "прем", "премєр", "прем'єр", "тур", "чемпіонат", "чемпіонату", "дотиснув", "лідерство",
    "partido", "victoria", "derrota", "penalti", "penalty", "liga",
}


def _url_fingerprint(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    parsed = urlparse(str(raw_url))
    if not parsed.netloc:
        return None
    path = parsed.path.rstrip('/').lower()
    if not path:
        return parsed.netloc.lower()
    return f"{parsed.netloc.lower()}{path}"


def _meaningful_tokens(text: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-zA-Z0-9а-яА-ЯёЁіІїЇєЄґҐáéíóúñüç]+", text.lower())
        if len(token) >= 3
    }
    return {token for token in tokens if token not in _STOPWORDS}


def _story_signature(title: str, description: str | None) -> set[str]:
    tokens = _meaningful_tokens(title)
    if description:
        tokens |= {t for t in _meaningful_tokens(description) if t in _MODEL_HINTS or t in _EVENT_TERMS or len(t) >= 5}
    return tokens


def _looks_like_same_event(sig_a: set[str], sig_b: set[str]) -> bool:
    shared = sig_a & sig_b
    event_a = sig_a & _EVENT_TERMS
    event_b = sig_b & _EVENT_TERMS
    if len(shared) >= 3 and (event_a or event_b):
        return True
    if len(shared) >= 2 and event_a and event_b:
        return True
    # Match-report headlines in Ukrainian/Russian/Spanish often describe the same
    # game with different verbs. If two specific team/entity tokens overlap and at
    # least one title clearly looks like a match report, treat them as one story.
    if len(shared) >= 2 and (event_a or event_b) and any(len(token) >= 5 for token in shared):
        return True
    return False


def _should_exclude_source(item: RawSourceItem) -> bool:
    raw_url = str(item.url) if item.url is not None else ''
    parsed = urlparse(raw_url)
    host = parsed.netloc.lower().replace('www.', '')
    source_name = (item.source_name or '').lower().replace('www.', '')
    path = parsed.path.lower()
    haystack = ' '.join((host, source_name))
    if any(snippet in haystack for snippet in _EXCLUDED_HOST_SNIPPETS):
        return True
    if host.endswith('.org') and not any(marker in path for marker in ('/news', '/article', '/articles', '/stories', '/story', '/press-release', '/press')):
        return True
    if any(marker in path for marker in ('/video/', '/videos/', '/watch', '/podcast', '/opinion/', '/liveblog')):
        return True
    return False


def normalize_source_items(items: list[RawSourceItem]) -> list[NormalizedSourceItem]:
    normalized: list[NormalizedSourceItem] = []
    seen_fingerprints: set[str] = set()
    for item in items:
        title = (item.title or '').strip()
        if not title or _should_exclude_source(item):
            continue

        normalized_title = normalize_title(title)
        if not normalized_title or item.published_at is None:
            continue

        fp = _url_fingerprint(str(item.url) if item.url is not None else None)
        if fp and fp in seen_fingerprints:
            continue
        if fp:
            seen_fingerprints.add(fp)

        normalized.append(
            NormalizedSourceItem(
                source_type=item.source_type or SourceType.OTHER,
                provider=item.provider,
                external_id=item.external_id,
                url=item.url,
                title=title,
                text=item.text,
                description=item.description,
                source_name=item.source_name.strip() or item.provider,
                source_language=item.source_language,
                published_at=item.published_at,
                metadata=item.metadata,
                normalized_title=normalized_title,
                canonical_key=normalized_title,
            )
        )
    return normalized


def normalize_articles(articles: list[RawArticle]) -> list[NormalizedSourceItem]:
    return normalize_source_items(articles)


def group_into_stories(items: list[NormalizedSourceItem]) -> list[StoryCandidate]:
    grouped: dict[str, list[NormalizedSourceItem]] = defaultdict(list)

    for item in items:
        matched_key: str | None = None
        item_live_prefix = live_prefix(item.title)
        item_sig = _story_signature(item.title, item.description)
        for key, grouped_items in grouped.items():
            exemplar = grouped_items[0]
            score = fuzz.token_set_ratio(item.normalized_title, key)
            ex_sig = _story_signature(exemplar.title, exemplar.description)
            sig_overlap = len(item_sig & ex_sig)
            if score >= 90:
                matched_key = key
                break
            existing_hosts = {urlparse(str(existing.url)).netloc for existing in grouped_items if existing.url}
            current_host = urlparse(str(item.url)).netloc if item.url else ''
            if score >= 84 and current_host and current_host in existing_hosts:
                matched_key = key
                break
            if sig_overlap >= 4 or _looks_like_same_event(item_sig, ex_sig):
                matched_key = key
                break
            exemplar_live_prefix = live_prefix(exemplar.title)
            if item_live_prefix and exemplar_live_prefix and item_live_prefix == exemplar_live_prefix:
                matched_key = key
                break
            description_a = (item.description or item.text or '').lower()
            description_b = (exemplar.description or exemplar.text or '').lower()
            if description_a and description_b and fuzz.token_set_ratio(description_a[:240], description_b[:240]) >= 90:
                matched_key = key
                break
        key = matched_key or item.canonical_key
        grouped[key].append(item)

    stories: list[StoryCandidate] = []
    for key, candidates in grouped.items():
        canonical_title = min(candidates, key=lambda candidate: len(candidate.title)).title
        story_hash = sha256(key.encode('utf-8')).hexdigest()
        stories.append(
            StoryCandidate(
                story_hash=story_hash,
                canonical_title=canonical_title,
                articles=sorted(candidates, key=lambda item: item.published_at, reverse=True),
            )
        )

    return stories



def filter_coherent_story_candidates(stories: list[StoryCandidate], query: str) -> list[StoryCandidate]:
    if len(stories) <= 2:
        return stories
    qtokens = _meaningful_tokens(query)
    def sig(story: StoryCandidate) -> set[str]:
        lead = story.articles[0]
        return _story_signature(story.canonical_title, lead.description) - qtokens
    sigs = [sig(s) for s in stories]
    scores = []
    for i, s in enumerate(stories):
        overlap_sum = 0
        for j, _ in enumerate(stories):
            if i == j:
                continue
            overlap_sum += len(sigs[i] & sigs[j])
        q_overlap = len((_story_signature(s.canonical_title, s.articles[0].description)) & qtokens)
        scores.append((overlap_sum, q_overlap, i))
    anchor_idx = max(scores)[2]
    anchor_sig = sigs[anchor_idx]
    filtered = []
    for story, ss in zip(stories, sigs):
        if story is stories[anchor_idx]:
            filtered.append(story)
            continue
        if len(anchor_sig & ss) >= 2:
            filtered.append(story)
            continue
        if len((_story_signature(story.canonical_title, story.articles[0].description)) & qtokens) >= max(1, min(2, len(qtokens))):
            filtered.append(story)
    return filtered or stories[:3]
