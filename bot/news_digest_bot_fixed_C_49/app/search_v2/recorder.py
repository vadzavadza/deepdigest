from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.schemas.sources import RawSourceItem


def _safe_slug(value: str, *, limit: int = 60) -> str:
    slug = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁіІїЇєЄґҐ._-]+", "-", value.strip().lower()).strip("-._")
    return (slug or "topic")[:limit]


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def raw_item_to_dict(item: RawSourceItem) -> dict[str, Any]:
    return {
        "provider": item.provider,
        "source_type": item.source_type.value,
        "external_id": item.external_id,
        "url": str(item.url) if item.url is not None else None,
        "title": item.title,
        "description": item.description,
        "text": item.text,
        "source_name": item.source_name,
        "source_language": item.source_language,
        "published_at": _iso(item.published_at),
        "metadata": dict(item.metadata or {}),
    }


def source_domain(raw_url: str | None, source_name: str | None = None) -> str:
    if raw_url:
        host = urlparse(raw_url).netloc.lower().replace("www.", "")
        if host:
            return host
    return (source_name or "unknown").lower().replace("www.", "")


@dataclass
class SearchRunRecord:
    run_id: str
    topic: str
    normalized_topic: str
    topic_kind: str
    from_dt: datetime
    to_dt: datetime
    query_variants: list[str]
    settings: dict[str, Any]
    pass_stats: list[dict[str, Any]] = field(default_factory=list)
    raw_candidates: list[dict[str, Any]] = field(default_factory=list)
    candidate_decisions: list[dict[str, Any]] = field(default_factory=list)
    final_items: list[dict[str, Any]] = field(default_factory=list)
    status: str = "running"
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    finished_at: datetime | None = None

    def add_pass(self, *, pass_index: int, query: str, raw_items: list[RawSourceItem], accepted_count: int, merged_count: int) -> None:
        raw_serialized = []
        for item in raw_items:
            serialized = raw_item_to_dict(item)
            serialized["pass_index"] = pass_index
            serialized["query"] = query
            raw_serialized.append(serialized)
            self.raw_candidates.append(serialized)
        self.pass_stats.append(
            {
                "pass_index": pass_index,
                "query": query,
                "raw_count": len(raw_items),
                "accepted_count": accepted_count,
                "merged_count": merged_count,
                "domains": dict(Counter(source_domain(item.get("url"), item.get("source_name")) for item in raw_serialized)),
            }
        )

    def add_decision(self, event: dict[str, Any]) -> None:
        self.candidate_decisions.append(event)

    def finish(self, *, status: str, final_items: list[RawSourceItem]) -> None:
        self.status = status
        self.finished_at = datetime.now(tz=timezone.utc)
        self.final_items = [raw_item_to_dict(item) for item in final_items]

    def as_dict(self) -> dict[str, Any]:
        reason_counts = Counter(str(event.get("reason") or "unknown") for event in self.candidate_decisions)
        status_counts = Counter(str(event.get("status") or "unknown") for event in self.candidate_decisions)
        final_domains = Counter(source_domain(item.get("url"), item.get("source_name")) for item in self.final_items)
        return {
            "schema_version": "search_run_v1",
            "run_id": self.run_id,
            "topic": self.topic,
            "normalized_topic": self.normalized_topic,
            "topic_kind": self.topic_kind,
            "from_dt": _iso(self.from_dt),
            "to_dt": _iso(self.to_dt),
            "created_at": _iso(self.created_at),
            "finished_at": _iso(self.finished_at),
            "status": self.status,
            "query_variants": list(self.query_variants),
            "settings": dict(self.settings),
            "pass_stats": list(self.pass_stats),
            "raw_candidates": list(self.raw_candidates),
            "candidate_decisions": list(self.candidate_decisions),
            "final_items": list(self.final_items),
            "summary": {
                "raw_count": len(self.raw_candidates),
                "decision_count": len(self.candidate_decisions),
                "final_count": len(self.final_items),
                "status_counts": dict(status_counts),
                "reason_counts": dict(reason_counts.most_common()),
                "final_domains": dict(final_domains),
            },
        }


class SearchRunRecorder:
    def __init__(self, *, enabled: bool, directory: str | Path) -> None:
        self.enabled = enabled
        self.directory = Path(directory)

    def start(
        self,
        *,
        topic: str,
        normalized_topic: str,
        topic_kind: str,
        from_dt: datetime,
        to_dt: datetime,
        query_variants: list[str],
        settings: dict[str, Any],
    ) -> SearchRunRecord | None:
        if not self.enabled:
            return None
        now = datetime.now(tz=timezone.utc)
        run_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{_safe_slug(topic, limit=32)}-{abs(hash((topic, now.timestamp()))) % 100000:05d}"
        return SearchRunRecord(
            run_id=run_id,
            topic=topic,
            normalized_topic=normalized_topic,
            topic_kind=topic_kind,
            from_dt=from_dt,
            to_dt=to_dt,
            query_variants=query_variants,
            settings=settings,
        )

    def write(self, record: SearchRunRecord | None) -> Path | None:
        if record is None or not self.enabled:
            return None
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{record.run_id}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record.as_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
        return path


def decision_event_from_candidate(
    *,
    source: str,
    topic: str,
    topic_kind: str,
    status: str,
    reason: str,
    score: int | float | None,
    directness_score: int | float | None,
    article_confidence: int | float | None,
    freshness_verified: bool | None,
    published_at_source: str | None,
    published_at: datetime | None,
    age_hours: float | None,
    url: str | None,
    title: str | None,
    pass_index: int | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "topic": topic,
        "topic_kind": topic_kind,
        "status": status,
        "reason": reason,
        "score": score,
        "directness_score": directness_score,
        "article_confidence": article_confidence,
        "freshness_verified": freshness_verified,
        "published_at_source": published_at_source,
        "published_at": _iso(published_at),
        "age_hours": age_hours,
        "url": url,
        "title": title,
        "domain": source_domain(url),
        "pass_index": pass_index,
        "query": query,
    }
