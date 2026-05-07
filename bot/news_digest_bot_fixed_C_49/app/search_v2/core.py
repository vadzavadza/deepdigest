from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from app.search_v2.article_filter import article_confidence, candidate_quality
from app.search_v2.strategy import SearchPlan
from app.search_v2.source_quality import source_quality_weight, source_authority_tier, source_vertical_mismatch, weak_source_allowed


class CandidateStatus(str, Enum):
    ACCEPTED = "accepted"
    WEAK_BUT_USABLE = "weak_but_usable"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    OLD = "old"
    HUB_PAGE = "hub_page"
    WRONG_ENTITY = "wrong_entity"


@dataclass(slots=True)
class FreshnessPolicy:
    soft_age_hours: int = 168
    hard_age_hours: int = 720
    followup_hard_age_hours: int = 72
    future_skew_hours: int = 12
    allow_weak_undated: bool = True
    weak_min_directness: int = 12
    weak_min_article_confidence: int = 0

    def floor_for(self, *, to_dt: datetime, plan: SearchPlan) -> datetime:
        hard_hours = self.hard_age_hours if plan.first_run else min(self.hard_age_hours, self.followup_hard_age_hours)
        floor = to_dt - timedelta(hours=max(hard_hours, 1))
        if floor.tzinfo is None:
            floor = floor.replace(tzinfo=timezone.utc)
        return floor.astimezone(timezone.utc)


@dataclass(slots=True)
class CandidateDecision:
    status: CandidateStatus
    reason: str
    score: int
    directness_score: int
    article_confidence: int
    freshness_verified: bool
    published_at: datetime | None
    published_at_source: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.status in {CandidateStatus.ACCEPTED, CandidateStatus.WEAK_BUT_USABLE}


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def candidate_age_hours(published_at: datetime | None, to_dt: datetime | None = None) -> float | None:
    published_at = _utc(published_at)
    if published_at is None:
        return None
    to_dt = _utc(to_dt) or datetime.now(tz=timezone.utc)
    return max((to_dt - published_at).total_seconds() / 3600.0, 0.0)

def _freshness_bucket(*, published_at: datetime | None, to_dt: datetime, verified: bool, policy: FreshnessPolicy) -> str:
    if published_at is None:
        return "undated"
    age_hours = candidate_age_hours(published_at, to_dt) or 0.0
    if not verified:
        return "weak_unverified"
    if age_hours <= policy.soft_age_hours:
        return "fresh"
    if age_hours <= policy.hard_age_hours:
        return "recent_but_not_latest"
    return "old"


def evaluate_candidate(
    plan: SearchPlan,
    *,
    url: str,
    title: str | None,
    description: str | None,
    published_at: datetime | None,
    published_at_source: str | None,
    to_dt: datetime,
    policy: FreshnessPolicy,
    search_annotation: bool = False,
    search_snippet: bool = False,
    source_name: str | None = None,
) -> CandidateDecision:
    """Universal candidate decision layer for v6.

    The old pipeline treated many checks as hard gates. v6 makes a balanced
    decision: verified recent articles are accepted; direct search-snippet
    articles without a verified date may be weak-but-usable; old/wrong/hub
    content is rejected with explicit reasons.
    """
    published_at = _utc(published_at)
    to_dt = _utc(to_dt) or datetime.now(tz=timezone.utc)
    quality = candidate_quality(plan, url=url, title=title, description=description)
    article_conf = article_confidence(url, title, description)
    qreason = quality.reason
    source_identity = source_name or urlparse(url).netloc
    source_weight = source_quality_weight(source_identity, plan.topic_kind)
    authority_tier = source_authority_tier(source_identity, plan.topic_kind)
    if source_vertical_mismatch(source_identity, plan.topic_kind):
        return CandidateDecision(CandidateStatus.WRONG_ENTITY, "source_vertical_mismatch", quality.score, quality.directness_score, article_conf, False, published_at, published_at_source, {"source_weight": source_weight, "authority_tier": authority_tier})
    if source_weight <= -80:
        return CandidateDecision(CandidateStatus.REJECTED, "blocked_source", quality.score, quality.directness_score, article_conf, False, published_at, published_at_source, {"source_weight": source_weight, "authority_tier": authority_tier})

    # Preserve hard safety gates from article_filter.
    if qreason in {
        "invalid_url",
        "bad_title_hint",
        "section_or_index_page",
        "topic_news_hub_page",
        "news_hub_page",
        "shallow_non_article_url",
        "non_article_media_or_live_page",
        "evergreen_or_service_content",
        "review_or_buying_guide",
    }:
        status = CandidateStatus.HUB_PAGE if "hub" in qreason or "section" in qreason or "shallow" in qreason else CandidateStatus.REJECTED
        return CandidateDecision(status, qreason, quality.score, quality.directness_score, article_conf, False, published_at, published_at_source)

    if qreason in {"wrong_entity_context", "generic_phrase_not_entity", "sports_drift_for_city", "finance_only_drift"}:
        return CandidateDecision(CandidateStatus.WRONG_ENTITY, qreason, quality.score, quality.directness_score, article_conf, False, published_at, published_at_source)

    verified = published_at_source in {"metadata", "url", "openrouter_native"}
    future_ceiling = to_dt + timedelta(hours=policy.future_skew_hours)
    if published_at is not None and published_at > future_ceiling:
        return CandidateDecision(CandidateStatus.REJECTED, "future_publish_date", quality.score, quality.directness_score, article_conf, verified, published_at, published_at_source)

    floor = policy.floor_for(to_dt=to_dt, plan=plan)
    if published_at is not None and published_at < floor:
        return CandidateDecision(CandidateStatus.OLD, "outside_hard_freshness_window", quality.score, quality.directness_score, article_conf, verified, published_at, published_at_source)

    bucket = _freshness_bucket(published_at=published_at, to_dt=to_dt, verified=verified, policy=policy)

    # Verified articles: do not throw away good 8-30 day candidates in broad/niche topics.
    if verified and quality.accepted and article_conf >= 0:
        return CandidateDecision(
            CandidateStatus.ACCEPTED,
            "accepted_verified" if bucket == "fresh" else "accepted_verified_recent_but_not_latest",
            quality.score,
            quality.directness_score,
            article_conf,
            True,
            published_at,
            published_at_source,
            {"freshness_bucket": bucket, "source_weight": source_weight, "authority_tier": authority_tier},
        )

    # Direct search annotations without a verified date are usable, but capped later.
    # v6.1: a site may block our HTTP fetch (403/DataDome/etc.) while OpenRouter
    # already gave us a strong article title. Do not require a snippet in that case,
    # but demand higher article confidence so price pages/hubs stay out.
    strong_title_only_annotation = (
        search_annotation
        and not search_snippet
        and quality.directness_score >= max(policy.weak_min_directness + 8, 24)
        and article_conf >= max(policy.weak_min_article_confidence + 2, 4)
    )
    strong_snippet_annotation = (
        search_annotation
        and search_snippet
        and quality.directness_score >= policy.weak_min_directness
        and article_conf >= policy.weak_min_article_confidence
    )
    can_use_weak = (
        policy.allow_weak_undated
        and (strong_snippet_annotation or strong_title_only_annotation)
        and qreason not in {"semantic_only_match", "no_direct_topic_evidence", "topic_score_below_threshold", "low_directness"}
        and weak_source_allowed(source_identity, plan.topic_kind)
    )
    if published_at is None and can_use_weak:
        return CandidateDecision(
            CandidateStatus.WEAK_BUT_USABLE,
            "accepted_search_snippet_weak_date",
            quality.score,
            quality.directness_score,
            article_conf,
            False,
            to_dt,
            "search_snippet",
            {"freshness_bucket": "weak_unverified", "source_weight": source_weight, "authority_tier": authority_tier},
        )

    if not quality.accepted:
        return CandidateDecision(CandidateStatus.REJECTED, qreason or "quality_rejected", quality.score, quality.directness_score, article_conf, verified, published_at, published_at_source)
    if published_at is None:
        return CandidateDecision(CandidateStatus.REJECTED, "missing_publish_date_not_usable", quality.score, quality.directness_score, article_conf, False, None, published_at_source)
    return CandidateDecision(CandidateStatus.REJECTED, "candidate_not_usable", quality.score, quality.directness_score, article_conf, verified, published_at, published_at_source)


@dataclass(slots=True)
class SearchDebugReport:
    raw_count: int = 0
    usable_count: int = 0
    accepted_count: int = 0
    weak_count: int = 0
    rejected_count: int = 0
    reason_counts: Counter[str] = field(default_factory=Counter)
    pass_stats: list[dict[str, Any]] = field(default_factory=list)

    def add_decision(self, decision: CandidateDecision) -> None:
        if decision.usable:
            self.usable_count += 1
            if decision.status == CandidateStatus.ACCEPTED:
                self.accepted_count += 1
            elif decision.status == CandidateStatus.WEAK_BUT_USABLE:
                self.weak_count += 1
        else:
            self.rejected_count += 1
        self.reason_counts[decision.reason] += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "raw_count": self.raw_count,
            "usable_count": self.usable_count,
            "accepted_count": self.accepted_count,
            "weak_count": self.weak_count,
            "rejected_count": self.rejected_count,
            "reason_counts": dict(self.reason_counts.most_common()),
            "pass_stats": self.pass_stats,
        }


def canonical_url_fingerprint(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    parsed = urlparse(raw_url)
    host = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/").lower()
    if not host:
        return None
    return f"{host}{path}"
