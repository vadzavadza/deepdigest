import re
import unicodedata

_SERVICE_PREFIXES = (
    "live:",
    "breaking:",
    "update:",
    "analysis:",
)

_SOURCE_SUFFIX_RE = re.compile(r"\s+(?:\||—|–|-|·)\s+(?:world news|business|news|live updates?)\s*$", re.IGNORECASE)
_SITE_TAIL_RE = re.compile(r"\s+(?:\||—|–|-)\s+[a-z0-9][a-z0-9 .&'-]{1,40}$", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]")


def _strip_source_suffixes(title: str) -> str:
    trimmed = title.strip()
    for _ in range(3):
        updated = _SOURCE_SUFFIX_RE.sub("", trimmed)
        updated = _SITE_TAIL_RE.sub("", updated)
        if updated == trimmed:
            break
        trimmed = updated.strip()
    return trimmed


def live_prefix(title: str) -> str | None:
    raw = unicodedata.normalize("NFKC", title).strip().lower()
    raw = _strip_source_suffixes(raw)
    prefix = None
    if ':' in raw:
        prefix = raw.split(':', 1)[0].strip()
    elif ' - ' in raw:
        prefix = raw.split(' - ', 1)[0].strip()
    if not prefix:
        return None
    if len(prefix.split()) > 6:
        return None
    if not any(marker in prefix for marker in ("latest", "live", "breaking", "update", "war")):
        return None
    normalized = _PUNCT_RE.sub(" ", prefix)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip() or None


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).strip().lower()
    normalized = _strip_source_suffixes(normalized)
    for prefix in _SERVICE_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
    normalized = _PUNCT_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()
