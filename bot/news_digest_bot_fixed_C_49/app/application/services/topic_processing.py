from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from rapidfuzz import fuzz

from app.application.services.deduplication import (
    filter_coherent_story_candidates,
    group_into_stories,
    normalize_source_items,
)
from app.application.services.source_collection import SourceCollectionService
from app.domain.enums import DeliveryMode, OutputLanguage, RelevanceLabel, SentType
from app.domain.policies.normalization import normalize_title
from app.domain.policies.ranking import (
    article_score,
    rank_stories,
    select_diverse_stories,
    select_primary_article,
    source_authority_tier,
    source_quality_weight,
)
from app.infrastructure.llm.base import LLMProvider
from app.infrastructure.repositories.job_runs import JobRunRepository
from app.infrastructure.repositories.sent_stories import SentStoryRepository
from app.infrastructure.repositories.stories import StoryRepository
from app.infrastructure.repositories.topics import TopicRepository
from app.infrastructure.sources.registry import SourceRegistry
from app.infrastructure.telegram.publisher import TelegramPublisher
from app.schemas.discovery import SourceFetchRequest, SourceFetchStats
from app.schemas.llm import RelevanceCheckResult, SummaryResult, TranslationResult
from app.schemas.publishing import PublishPayload, PublishStoryItem
from app.schemas.sources import NormalizedSourceItem
from app.shared.cost_budget import CostBudget
from app.shared.logging import get_logger
from app.shared.settings import get_settings

logger = get_logger(__name__)


@dataclass(slots=True)
class TopicProcessingOutcome:
    found_articles: int
    unique_stories: int
    sent_count: int
    source_stats: list[SourceFetchStats] = field(default_factory=list)
    skipped_already_sent: int = 0
    skipped_immediate_repeat: int = 0
    skipped_low_quality: int = 0
    relevance_checks: int = 0
    relevance_skipped_native: int = 0
    budget_spent_usd: float = 0.0
    budget_remaining_usd: float = 0.0
    budget_over_soft_limit: bool = False


class TopicProcessingService:
    def __init__(
        self,
        *,
        session,
        source_registry: SourceRegistry,
        llm_provider: LLMProvider,
        publisher: TelegramPublisher | None = None,
    ) -> None:
        self._session = session
        self._topic_repository = TopicRepository(session)
        self._job_run_repository = JobRunRepository(session)
        self._story_repository = StoryRepository(session)
        self._sent_story_repository = SentStoryRepository(session)
        self._source_registry = source_registry
        self._source_collection_service = SourceCollectionService(source_registry)
        self._llm_provider = llm_provider
        self._publisher = publisher

    async def process_topic(
        self,
        topic_id: int,
        *,
        force: bool = False,
        window_override_hours: int | None = None,
    ) -> TopicProcessingOutcome:
        settings = get_settings()
        budget = CostBudget(
            hard_limit_usd=max(settings.news_topic_hard_budget_usd, 0.0),
            soft_limit_usd=max(min(settings.news_topic_soft_budget_usd, settings.news_topic_hard_budget_usd), 0.0),
            stop_margin_usd=max(settings.news_topic_stop_margin_usd, 0.0),
        )
        self._source_registry.attach_budget(budget)
        attach_budget = getattr(self._llm_provider, "attach_budget", None)
        if callable(attach_budget):
            attach_budget(budget)

        try:
            await self._session.rollback()
        except Exception:
            pass
        topic = await self._topic_repository.get_by_id(topic_id)
        if topic is None:
            raise ValueError(f"Topic {topic_id} not found")

        window_to = datetime.now(tz=timezone.utc)
        has_history = await self._sent_story_repository.has_any_for_topic(topic_id=topic_id)
        last_sent_at = await self._sent_story_repository.get_last_sent_at(topic_id=topic_id)
        recent_sent_count = await self._sent_story_repository.get_recent_sent_count(topic_id=topic_id, hours=72)
        if last_sent_at is not None and last_sent_at.tzinfo is None:
            last_sent_at = last_sent_at.replace(tzinfo=timezone.utc)
        if last_sent_at is not None:
            last_sent_at = last_sent_at.astimezone(timezone.utc)
        thin_recent_history = has_history and recent_sent_count < min(3, settings.max_stories_per_post)
        immediate_repeat = (
            last_sent_at is not None
            and (window_to - last_sent_at) <= timedelta(minutes=settings.immediate_repeat_guard_minutes)
        )
        if window_override_hours is not None:
            window_from = window_to - timedelta(hours=window_override_hours)
        elif immediate_repeat:
            window_from = max(last_sent_at, window_to - timedelta(hours=2))
        elif force and thin_recent_history:
            window_from = window_to - timedelta(hours=72)
        elif force:
            window_from = window_to - timedelta(days=7)
        elif thin_recent_history:
            window_from = window_to - timedelta(hours=72)
        elif has_history:
            window_from = window_to - timedelta(hours=48)
        elif topic.mode == DeliveryMode.DAILY_DIGEST.value:
            window_from = window_to - timedelta(hours=72)
        else:
            window_from = window_to - timedelta(days=7)

        job_run = await self._job_run_repository.start(topic_id=topic_id)
        await self._session.commit()
        logger.info(
            "job_start",
            run_id=job_run.run_id,
            topic_id=topic_id,
            query_text=topic.query_text,
            mode=topic.mode,
            window_from=window_from.isoformat(),
            window_to=window_to.isoformat(),
            force=force,
            recent_sent_count=recent_sent_count,
            thin_recent_history=thin_recent_history,
            immediate_repeat=immediate_repeat,
            last_sent_at=last_sent_at.isoformat() if last_sent_at else None,
            budget_hard_limit_usd=budget.hard_limit_usd,
            budget_soft_limit_usd=budget.soft_limit_usd,
        )

        relevance_checks = 0
        relevance_skipped_native = 0
        skipped_already_sent = 0
        skipped_immediate_repeat = 0
        skipped_low_quality = 0

        try:
            raw_items, collection_result = await self._source_collection_service.collect(
                SourceFetchRequest(
                    query=topic.query_text,
                    from_dt=window_from,
                    to_dt=window_to,
                    limit=settings.max_articles_per_provider,
                )
            )
            normalized_items = normalize_source_items(raw_items)
            story_candidates = rank_stories(
                filter_coherent_story_candidates(group_into_stories(normalized_items), topic.query_text)
            )

            recent_story_ids = await self._sent_story_repository.get_all_story_ids(topic_id=topic_id)
            sent_signatures = await self._sent_story_repository.get_sent_story_signatures(topic_id=topic_id)
            sent_url_fingerprints = await self._sent_story_repository.get_sent_url_fingerprints(topic_id=topic_id)
            selected_candidates = []
            max_relevance_checks = max(settings.llm_relevance_max_checks_per_topic, 0)

            for story in story_candidates:
                primary = select_primary_article(story.articles)
                primary_fp = self._url_fingerprint(str(primary.url) if primary.url is not None else None)
                if primary_fp and primary_fp in sent_url_fingerprints:
                    skipped_already_sent += 1
                    logger.info(
                        "candidate_skipped_already_sent_url",
                        topic_id=topic_id,
                        story_hash=story.story_hash,
                        source_name=primary.source_name,
                    )
                    continue

                primary_score = article_score(primary)
                source_weight = source_quality_weight(primary.source_name, str(primary.metadata.get("topic_kind", "")))
                authority_tier = source_authority_tier(primary.source_name, str(primary.metadata.get("topic_kind", "")))
                if primary.url is None or primary_score < 0 or source_weight < 0.0:
                    skipped_low_quality += 1
                    logger.info(
                        "candidate_skipped_low_quality_before_llm",
                        topic_id=topic_id,
                        story_hash=story.story_hash,
                        source_name=primary.source_name,
                        article_score=primary_score,
                        source_weight=source_weight,
                        authority_tier=authority_tier,
                    )
                    continue

                if immediate_repeat:
                    is_weak_candidate = primary.metadata.get("freshness_verified") is False
                    not_newer_than_last_digest = bool(
                        last_sent_at and primary.published_at <= last_sent_at + timedelta(minutes=2)
                    )
                    if is_weak_candidate or not_newer_than_last_digest or source_weight < 12.0:
                        skipped_immediate_repeat += 1
                        logger.info(
                            "candidate_skipped_immediate_repeat_guard",
                            topic_id=topic_id,
                            story_hash=story.story_hash,
                            source_name=primary.source_name,
                            source_weight=source_weight,
                            authority_tier=authority_tier,
                            freshness_verified=primary.metadata.get("freshness_verified"),
                            published_at=primary.published_at.isoformat(),
                            last_sent_at=last_sent_at.isoformat() if last_sent_at else None,
                        )
                        continue

                story_signature = normalize_title(story.canonical_title)
                if any(fuzz.token_set_ratio(story_signature, existing) >= 90 for existing in sent_signatures):
                    skipped_already_sent += 1
                    logger.info(
                        "candidate_skipped_already_sent_signature",
                        topic_id=topic_id,
                        story_hash=story.story_hash,
                        source_name=primary.source_name,
                    )
                    continue

                if self._can_skip_relevance_check(primary, settings=settings):
                    relevance_skipped_native += 1
                    logger.info(
                        "candidate_relevance_skipped_native_judge",
                        topic_id=topic_id,
                        story_hash=story.story_hash,
                        source_name=primary.source_name,
                        native_topic_match=primary.metadata.get("native_topic_match"),
                        candidate_status=primary.metadata.get("candidate_status"),
                    )
                else:
                    if relevance_checks >= max_relevance_checks:
                        logger.info(
                            "candidate_skipped_relevance_budget",
                            topic_id=topic_id,
                            story_hash=story.story_hash,
                            max_relevance_checks=max_relevance_checks,
                        )
                        continue
                    relevance_checks += 1
                    relevance = await self._safe_check_relevance(topic.query_text, primary)
                    if relevance.relevance == RelevanceLabel.REJECT:
                        logger.info(
                            "candidate_rejected_by_llm",
                            topic_id=topic_id,
                            story_hash=story.story_hash,
                            source_name=primary.source_name,
                            reason=relevance.reason,
                        )
                        continue

                db_story = await self._story_repository.upsert_story(
                    topic_id=topic_id,
                    story_hash=story.story_hash,
                    canonical_title=story.canonical_title,
                    first_seen_at=story.articles[-1].published_at,
                    last_seen_at=story.articles[0].published_at,
                )
                if db_story.id in recent_story_ids:
                    skipped_already_sent += 1
                    logger.info(
                        "candidate_skipped_recent_story_id",
                        topic_id=topic_id,
                        story_hash=story.story_hash,
                        source_name=primary.source_name,
                    )
                    continue
                selected_candidates.append((story, db_story))

            payload_items: list[PublishStoryItem] = []
            persisted_sent_story_ids: list[int] = []
            max_items = min(settings.max_stories_per_post, 3 if not has_history else settings.max_stories_per_post)

            if selected_candidates:
                selected_map = {story.story_hash: (story, db_story) for story, db_story in selected_candidates}
                diverse_stories = select_diverse_stories([story for story, _ in selected_candidates], max_items)
                ordered_candidates = [selected_map[story.story_hash] for story in diverse_stories if story.story_hash in selected_map]
            else:
                ordered_candidates = []

            weak_freshness_sent = 0
            max_weak_freshness = max(0, settings.openrouter_max_weak_freshness_items_per_digest)

            for story, db_story in ordered_candidates[:max_items]:
                primary = select_primary_article(story.articles)
                is_weak_freshness = primary.metadata.get("freshness_verified") is False
                if immediate_repeat and is_weak_freshness:
                    skipped_immediate_repeat += 1
                    logger.info(
                        "story_skipped_immediate_repeat_weak_freshness",
                        topic_id=topic_id,
                        story_hash=story.story_hash,
                        source_name=primary.source_name,
                    )
                    continue
                if is_weak_freshness and weak_freshness_sent >= max_weak_freshness:
                    skipped_low_quality += 1
                    logger.info(
                        "story_skipped_weak_freshness_cap",
                        topic_id=topic_id,
                        story_hash=story.story_hash,
                        source_name=primary.source_name,
                        published_at_source=primary.metadata.get("published_at_source"),
                    )
                    continue
                primary_score = article_score(primary)
                source_weight = source_quality_weight(primary.source_name, str(primary.metadata.get("topic_kind", "")))
                authority_tier = source_authority_tier(primary.source_name, str(primary.metadata.get("topic_kind", "")))
                if source_weight < 0.0 or (is_weak_freshness and source_weight < 12.0):
                    skipped_low_quality += 1
                    logger.info(
                        "story_skipped_low_source_quality",
                        topic_id=topic_id,
                        story_hash=story.story_hash,
                        source_name=primary.source_name,
                        source_weight=source_weight,
                        authority_tier=authority_tier,
                        freshness_verified=primary.metadata.get("freshness_verified"),
                    )
                    continue
                if primary.url is None or primary_score < 0:
                    skipped_low_quality += 1
                    logger.info(
                        "story_skipped_without_url_or_low_score",
                        topic_id=topic_id,
                        story_hash=story.story_hash,
                        source_name=primary.source_name,
                        article_score=primary_score,
                    )
                    continue

                summary_result = await self._safe_summarize(topic.query_text, primary)
                summary = summary_result.summary
                if topic.output_language != (primary.source_language or topic.output_language):
                    translation = await self._safe_translate(summary, topic.output_language)
                    summary = translation.translated_text

                if is_weak_freshness:
                    weak_freshness_sent += 1

                payload_items.append(
                    PublishStoryItem(
                        title=story.canonical_title,
                        summary=summary,
                        source_name=primary.source_name,
                        source_language=primary.source_language or "unknown",
                        link=primary.url,
                        sent_type=SentType.NEW,
                    )
                )
                persisted_sent_story_ids.append(db_story.id)

            if payload_items or settings.publish_empty_digest:
                payload = PublishPayload(
                    topic_id=topic.id,
                    query_text=topic.query_text,
                    output_language=topic.output_language,
                    mode=topic.mode,
                    generated_at=datetime.now(tz=timezone.utc),
                    items=payload_items,
                )
                if self._publisher is not None and topic.channel is not None:
                    await self._publisher.publish(
                        channel_chat_id=topic.channel.telegram_chat_id,
                        payload=payload,
                    )

            for story_id, item in zip(persisted_sent_story_ids, payload_items, strict=True):
                await self._sent_story_repository.add(
                    topic_id=topic.id,
                    story_id=story_id,
                    primary_article_id=None,
                    primary_url=str(item.link),
                    sent_type=item.sent_type.value,
                )

            counters = {
                **budget.as_counters(),
                "skipped_already_sent": skipped_already_sent,
                "skipped_immediate_repeat": skipped_immediate_repeat,
                "skipped_low_quality": skipped_low_quality,
                "relevance_checks": relevance_checks,
                "relevance_skipped_native": relevance_skipped_native,
            }
            await self._job_run_repository.finish_success(
                job_run,
                found_articles=collection_result.items_count,
                unique_stories=len(story_candidates),
                sent_count=len(payload_items),
                counters=counters,
            )
            await self._session.commit()
            logger.info(
                "publish_done",
                run_id=job_run.run_id,
                topic_id=topic_id,
                found_articles=collection_result.items_count,
                unique_stories=len(story_candidates),
                sent_count=len(payload_items),
                skipped_already_sent=skipped_already_sent,
                skipped_immediate_repeat=skipped_immediate_repeat,
                skipped_low_quality=skipped_low_quality,
                relevance_checks=relevance_checks,
                relevance_skipped_native=relevance_skipped_native,
                budget_spent_usd=budget.spent_usd,
                budget_remaining_usd=budget.remaining_usd,
            )
            return TopicProcessingOutcome(
                found_articles=collection_result.items_count,
                unique_stories=len(story_candidates),
                sent_count=len(payload_items),
                source_stats=collection_result.stats,
                skipped_already_sent=skipped_already_sent,
                skipped_immediate_repeat=skipped_immediate_repeat,
                skipped_low_quality=skipped_low_quality,
                relevance_checks=relevance_checks,
                relevance_skipped_native=relevance_skipped_native,
                budget_spent_usd=budget.spent_usd,
                budget_remaining_usd=budget.remaining_usd,
                budget_over_soft_limit=budget.is_over_soft_limit,
            )
        except Exception as exc:
            try:
                await self._session.rollback()
            except Exception:
                pass
            try:
                await self._job_run_repository.finish_failed(
                    job_run,
                    error_text=f"{type(exc).__name__}: {exc}"[:1000],
                    counters=budget.as_counters(),
                )
                await self._session.commit()
            except Exception:
                try:
                    await self._session.rollback()
                except Exception:
                    pass
            logger.exception("job_failed", run_id=job_run.run_id, topic_id=topic_id, error_type=type(exc).__name__)
            raise

    async def _safe_check_relevance(self, topic_query: str, article: NormalizedSourceItem) -> RelevanceCheckResult:
        try:
            return await self._llm_provider.check_relevance(topic_query=topic_query, article=article)
        except Exception:
            haystack = " ".join(filter(None, [article.title, article.description, article.text])).lower()
            if topic_query.lower() in haystack:
                return RelevanceCheckResult(relevance=RelevanceLabel.RELEVANT, reason="fallback_keyword_match")
            return RelevanceCheckResult(relevance=RelevanceLabel.WEAK, reason="fallback_llm_error_or_budget_exhausted")

    async def _safe_summarize(self, topic_query: str, article: NormalizedSourceItem) -> SummaryResult:
        try:
            return await self._llm_provider.summarize_article(topic_query=topic_query, article=article)
        except Exception:
            text = article.description or article.text or article.title
            short = text.strip() if text else article.title
            if len(short) < 20:
                short = f"{article.title}. Source: {article.source_name}."
            return SummaryResult(summary=short[:500])

    async def _safe_translate(self, text: str, target_language: str) -> TranslationResult:
        try:
            language_enum = OutputLanguage(target_language)
        except Exception:
            return TranslationResult(translated_text=text)

        try:
            return await self._llm_provider.translate_text(text=text, target_language=language_enum)
        except Exception:
            return TranslationResult(translated_text=text)

    @staticmethod
    def _url_fingerprint(raw_url: str | None) -> str | None:
        if not raw_url:
            return None
        parsed = urlparse(raw_url)
        if not parsed.netloc:
            return None
        return f"{parsed.netloc.lower()}{parsed.path.rstrip('/').lower()}"

    @staticmethod
    def _can_skip_relevance_check(article: NormalizedSourceItem, *, settings: Any) -> bool:
        if not settings.llm_skip_relevance_for_native_judged_candidates:
            return False
        if article.metadata.get("native_judge") is not True:
            return False
        try:
            native_topic_match = float(article.metadata.get("native_topic_match") or 0.0)
        except Exception:
            native_topic_match = 0.0
        if native_topic_match < max(0.0, min(settings.llm_native_relevance_min_topic_match, 1.0)):
            return False
        if str(article.metadata.get("candidate_status") or "") not in {"accepted", "weak_but_usable"}:
            return False
        try:
            directness = int(article.metadata.get("directness_score") or 0)
        except Exception:
            directness = 0
        return directness >= max(10, settings.openrouter_search_snippet_fallback_min_directness)
