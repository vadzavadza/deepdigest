from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import HttpUrl, TypeAdapter

from app.domain.enums import SourceType
from app.schemas.sources import RawSourceItem
from app.search_v2 import build_search_plan, extract_html_metadata, article_confidence, candidate_quality, evaluate_candidate, FreshnessPolicy, candidate_age_hours
from app.search_v2.recorder import SearchRunRecorder, SearchRunRecord, decision_event_from_candidate
from app.search_v2.source_quality import source_quality_weight, source_authority_tier
from app.shared.cost_budget import BudgetExhausted, CostBudget
from app.shared.logging import get_logger
from app.shared.settings import get_settings

logger = get_logger(__name__)

_URL_RE = re.compile(r"https?://\S+")
_HTTP_URL = TypeAdapter(HttpUrl)

_HOST_BLOCKLIST = {
    "youtube.com", "www.youtube.com", "youtu.be",
    "wikipedia.org", "www.wikipedia.org", "wikimedia.org", "wikinews.org",
    "iheart.com", "www.iheart.com", "reddit.com", "www.reddit.com",
    "facebook.com", "www.facebook.com", "instagram.com", "www.instagram.com",
    "tiktok.com", "www.tiktok.com", "x.com", "twitter.com", "www.twitter.com",
    "linkedin.com", "www.linkedin.com",
}

_NON_NEWS_HOST_HINTS = (
    "youtube", "youtu", "podcast", "wiki", "wikimedia", "iheart", "reddit", "tiktok", "facebook", "instagram",
)

_NEWS_PATH_HINTS = (
    "/news", "/article", "/articles", "/world", "/business", "/markets", "/politics", "/technology",
    "/tech", "/economy", "/international", "/story", "/stories", "/latest", "/live", "/202",
)

_TITLE_BLOCK_HINTS = (
    "youtube", "video", "podcast", "playlist", "channel", "wikipedia", "category:", "tag:",
)


def _looks_like_news_hub_title(title: str | None, path: str) -> bool:
    if not title:
        return False
    title_norm = re.sub(r"\s+", " ", title.lower()).strip()
    left = re.split(r"\s*(?:\||-|–|—|:)\s*", title_norm, maxsplit=1)[0].strip()
    words = re.findall(r"[a-z0-9]+", left)
    if len(words) <= 6 and (left.endswith(" news") or left.endswith(" latest news") or left.startswith("latest ") and left.endswith(" news")):
        return True
    if path.rstrip("/") in {"", "/news", "/latest", "/latest-news", "/world", "/business", "/politics", "/markets", "/sport", "/sports", "/technology", "/tech"} and " news" in title_norm:
        return True
    return False


class OpenRouterWebSearchSource:
    """Fetch candidate news links via OpenRouter web search.

    Strategy:
    1) Use the current server tool `openrouter:web_search`.
    2) Try multiple news-oriented query variants and merge unique results.
    3) If no annotations/results are returned, fall back to the legacy `web` plugin.
    4) If annotations are missing, try to recover URLs from markdown/plain text.
    """

    name = "openrouter_web_search"
    source_type = SourceType.WEB_SEARCH

    def __init__(self, *, model: str | None = None, timeout_seconds: float = 45.0, budget: CostBudget | None = None) -> None:
        settings = get_settings()
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._api_key = settings.openrouter_api_key
        self._model = model or settings.openrouter_search_model or settings.openrouter_default_model
        self._timeout_seconds = timeout_seconds
        self._budget = budget
        self._max_results = max(settings.openrouter_web_search_max_results, 1)
        self._topic_budget_usd = max(settings.news_topic_hard_budget_usd, settings.openrouter_topic_budget_usd, 0.0)
        self._soft_budget_usd = max(settings.news_topic_soft_budget_usd, 0.0)
        self._reserved_llm_budget_usd = max(settings.openrouter_reserved_llm_budget_usd, 0.0)
        self._normal_max_calls = max(settings.openrouter_web_search_normal_max_calls, 1)
        self._rescue_max_calls = max(settings.openrouter_web_search_rescue_max_calls, self._normal_max_calls)
        self._search_result_cost_usd = max(settings.openrouter_search_result_cost_usd, 0.0)
        self._search_call_model_reserve_usd = max(settings.openrouter_search_call_model_reserve_usd, 0.0)
        self._results_per_call = max(settings.openrouter_web_search_results_per_call, 1)
        self._max_calls_per_topic = max(settings.openrouter_web_search_max_calls_per_topic, 1)
        self._min_quality_candidates = max(settings.openrouter_min_quality_candidates, 1)
        self._allow_plugin_fallback = settings.openrouter_allow_plugin_fallback
        self._native_news_agent_enabled = settings.openrouter_native_news_agent_enabled
        self._native_judge_min_topic_match = max(0.0, min(settings.openrouter_native_judge_min_topic_match, 1.0))
        self._native_judge_max_candidates = max(settings.openrouter_native_judge_max_candidates, 1)
        self._native_reject_weak_sources = settings.openrouter_native_reject_weak_sources
        self._debug_rejections = settings.openrouter_debug_rejections
        self._max_article_age_hours = max(settings.openrouter_max_article_age_hours, 1)
        self._require_verified_publish_date = settings.openrouter_require_verified_publish_date
        self._allow_weak_publish_dates = settings.openrouter_allow_weak_publish_dates
        self._allow_undated_fallback = settings.openrouter_allow_undated_fallback
        self._future_skew_hours = max(settings.openrouter_future_skew_hours, 0)
        self._allow_search_snippet_fallback = settings.openrouter_allow_search_snippet_fallback
        self._search_snippet_fallback_min_directness = max(settings.openrouter_search_snippet_fallback_min_directness, 1)
        self._search_snippet_fallback_min_confidence = max(settings.openrouter_search_snippet_fallback_min_confidence, 0)
        self._adaptive_target_candidates = max(settings.openrouter_adaptive_target_candidates, 1)
        self._min_search_passes = max(settings.openrouter_min_search_passes, 1)
        self._freshness_policy = FreshnessPolicy(
            soft_age_hours=self._max_article_age_hours,
            hard_age_hours=max(settings.openrouter_verified_hard_max_article_age_hours, self._max_article_age_hours),
            followup_hard_age_hours=max(settings.openrouter_followup_hard_max_article_age_hours, 24),
            future_skew_hours=self._future_skew_hours,
            allow_weak_undated=self._allow_search_snippet_fallback,
            weak_min_directness=self._search_snippet_fallback_min_directness,
            weak_min_article_confidence=self._search_snippet_fallback_min_confidence,
        )
        self._debug_dump_enabled = settings.search_debug_dump_enabled or settings.app_debug
        self._debug_dump_dir = settings.search_debug_dump_dir


    def attach_budget(self, budget: CostBudget | None) -> None:
        self._budget = budget

    def _estimated_search_call_cost(self, limit: int) -> float:
        return max(limit, 1) * self._search_result_cost_usd + self._search_call_model_reserve_usd

    async def fetch(
        self,
        query: str,
        from_dt: datetime,
        to_dt: datetime,
        limit: int,
    ) -> list[RawSourceItem]:
        plan = build_search_plan(query, from_dt=from_dt, to_dt=to_dt, first_run=(to_dt - from_dt) > timedelta(hours=60))
        target_limit = max(1, min(limit, self._max_results))
        results_per_call = max(1, min(self._results_per_call, target_limit))
        hard_max_calls = self._allowed_search_calls(results_per_call, budget_usd=self._topic_budget_usd)
        soft_max_calls = self._allowed_search_calls(results_per_call, budget_usd=self._soft_budget_usd)
        max_calls = min(hard_max_calls, self._rescue_max_calls)
        normal_calls = max(1, min(max_calls, soft_max_calls, self._normal_max_calls))
        queries = plan.query_variants[:max_calls]
        merged: list[RawSourceItem] = []
        seen_urls: set[str] = set()
        rescue_pool: list[RawSourceItem] = []
        rescue_seen: set[str] = set()

        logger.info(
            "source_fetch_plan",
            source=self.name,
            query=query,
            topic_kind=plan.topic_kind,
            target_limit=target_limit,
            results_per_call=results_per_call,
            max_calls=max_calls,
            normal_calls=normal_calls,
            budget_usd=self._topic_budget_usd,
            soft_budget_usd=self._soft_budget_usd,
            reserved_llm_budget_usd=self._reserved_llm_budget_usd,
            query_variants=queries,
        )

        adaptive_target = min(target_limit, max(self._min_quality_candidates, self._adaptive_target_candidates))
        min_passes = min(max_calls, self._min_search_passes)
        pass_stats: list[dict[str, Any]] = []
        recorder = SearchRunRecorder(enabled=self._debug_dump_enabled, directory=self._debug_dump_dir)
        record = recorder.start(
            topic=query,
            normalized_topic=plan.normalized_query,
            topic_kind=plan.topic_kind,
            from_dt=from_dt,
            to_dt=to_dt,
            query_variants=queries,
            settings={
                "target_limit": target_limit,
                "results_per_call": results_per_call,
                "max_calls": max_calls,
                "normal_calls": normal_calls,
                "budget_usd": self._topic_budget_usd,
                "soft_budget_usd": self._soft_budget_usd,
                "reserved_llm_budget_usd": self._reserved_llm_budget_usd,
                "min_quality_candidates": self._min_quality_candidates,
                "allow_search_snippet_fallback": self._allow_search_snippet_fallback,
                "max_article_age_hours": self._max_article_age_hours,
                "verified_hard_max_article_age_hours": self._freshness_policy.hard_age_hours,
                "native_news_agent_enabled": self._native_news_agent_enabled,
                "native_judge_min_topic_match": self._native_judge_min_topic_match,
                "native_judge_max_candidates": self._native_judge_max_candidates,
            },
        )

        for pass_index, current_query in enumerate(queries, start=1):
            payload = await self._call_server_tool(query=current_query, from_dt=from_dt, to_dt=to_dt, limit=results_per_call, broad_topic=plan.broad_topic, topic_kind=plan.topic_kind)
            raw_items = self._extract_items_from_payload(payload, results_per_call)
            self._append_unique_raw(rescue_pool, rescue_seen, raw_items)
            items = await self._enrich_and_filter_recent(
                raw_items,
                from_dt=from_dt,
                to_dt=to_dt,
                plan=plan,
                allow_search_snippet_fallback=False,
                record=record,
                pass_index=pass_index,
                query_text=current_query,
            )
            before_count = len(merged)
            self._merge_unique(merged, seen_urls, items, target_limit)
            pass_stats.append({
                "pass": pass_index,
                "query": current_query,
                "raw": len(raw_items),
                "accepted": len(items),
                "merged_after_pass": len(merged),
            })
            if record is not None:
                record.add_pass(
                    pass_index=pass_index,
                    query=current_query,
                    raw_items=raw_items,
                    accepted_count=len(items),
                    merged_count=len(merged),
                )
            logger.info(
                "source_fetch_pass",
                source=self.name,
                pass_index=pass_index,
                raw_count=len(raw_items),
                accepted_count=len(items),
                added_count=len(merged) - before_count,
                merged_count=len(merged),
                adaptive_target=adaptive_target,
                query=current_query,
            )
            # Do not make the user press the button twice: keep going until we have
            # a usable candidate pool, but stop early when the pool is already good.
            if len(merged) >= target_limit:
                break
            if pass_index >= normal_calls:
                # Rescue pass is allowed only when the normal budget did not produce
                # enough usable candidates and the topic is not highly ambiguous.
                if len(merged) >= adaptive_target:
                    break
                if plan.topic_kind in {"ambiguous_acronym", "ambiguous_geo"}:
                    break

        if len(merged) < min(self._min_quality_candidates, target_limit) and rescue_pool and self._allow_search_snippet_fallback:
            rescue_items = await self._enrich_and_filter_recent(
                rescue_pool,
                from_dt=from_dt,
                to_dt=to_dt,
                plan=plan,
                allow_search_snippet_fallback=True,
                record=record,
                pass_index=0,
                query_text="rescue_pool",
            )
            self._merge_unique(merged, seen_urls, rescue_items, target_limit)

        if merged:
            logger.info("source_fetch_success", source=self.name, strategy="server_tool_budgeted", count=len(merged), pass_stats=pass_stats)
            if record is not None:
                record.finish(status="success", final_items=merged)
                dump_path = recorder.write(record)
                if dump_path is not None:
                    logger.info("search_debug_dump_written", source=self.name, path=str(dump_path), run_id=record.run_id)
            return merged

        if self._allow_plugin_fallback:
            for current_query in queries:
                payload = await self._call_plugin_fallback(query=current_query, from_dt=from_dt, to_dt=to_dt, limit=results_per_call)
                raw_items = self._extract_items_from_payload(payload, results_per_call)
                items = await self._enrich_and_filter_recent(
                    raw_items,
                    from_dt=from_dt,
                    to_dt=to_dt,
                    plan=plan,
                    allow_search_snippet_fallback=self._allow_search_snippet_fallback,
                    record=record,
                    pass_index=100,
                    query_text=current_query,
                )
                self._merge_unique(merged, seen_urls, items, target_limit)
                if len(merged) >= target_limit:
                    logger.info("source_fetch_success", source=self.name, strategy="plugin_fallback_budgeted", count=len(merged))
                    if record is not None:
                        record.finish(status="success_plugin_fallback", final_items=merged)
                        dump_path = recorder.write(record)
                        if dump_path is not None:
                            logger.info("search_debug_dump_written", source=self.name, path=str(dump_path), run_id=record.run_id)
                    return merged

        if merged:
            logger.info("source_fetch_success", source=self.name, strategy="plugin_fallback_budgeted", count=len(merged))
            if record is not None:
                record.finish(status="success_plugin_fallback", final_items=merged)
                dump_path = recorder.write(record)
                if dump_path is not None:
                    logger.info("search_debug_dump_written", source=self.name, path=str(dump_path), run_id=record.run_id)
            return merged

        logger.info("source_fetch_empty", source=self.name, query=query)
        if record is not None:
            record.finish(status="empty", final_items=[])
            dump_path = recorder.write(record)
            if dump_path is not None:
                logger.info("search_debug_dump_written", source=self.name, path=str(dump_path), run_id=record.run_id)
        return []

    def _allowed_search_calls(self, results_per_call: int, *, budget_usd: float | None = None) -> int:
        if self._search_result_cost_usd <= 0:
            return self._max_calls_per_topic
        usable_budget = max((self._topic_budget_usd if budget_usd is None else budget_usd) - self._reserved_llm_budget_usd, 0.0)
        per_call_cost = self._estimated_search_call_cost(results_per_call)
        if per_call_cost <= 0:
            return self._max_calls_per_topic
        affordable = int(usable_budget // per_call_cost)
        return max(1, min(self._max_calls_per_topic, affordable))
    @staticmethod
    def _build_queries(query: str, from_dt: datetime, to_dt: datetime) -> list[str]:
        return build_search_plan(query, from_dt=from_dt, to_dt=to_dt, first_run=(to_dt - from_dt) > timedelta(hours=60)).query_variants


    @staticmethod
    def _is_broad_topic(query: str) -> bool:
        return build_search_plan(query, from_dt=datetime.now(tz=timezone.utc)-timedelta(days=7), to_dt=datetime.now(tz=timezone.utc), first_run=True).broad_topic


    @staticmethod
    def _merge_unique(target: list[RawSourceItem], seen_urls: set[str], incoming: list[RawSourceItem], limit: int) -> None:
        for item in incoming:
            raw_url = str(item.url) if item.url is not None else None
            if raw_url is None or raw_url in seen_urls:
                continue
            seen_urls.add(raw_url)
            target.append(item)
            if len(target) >= limit:
                return

    @staticmethod
    def _append_unique_raw(target: list[RawSourceItem], seen_urls: set[str], incoming: list[RawSourceItem]) -> None:
        for item in incoming:
            raw_url = str(item.url) if item.url is not None else None
            if raw_url is None or raw_url in seen_urls:
                continue
            seen_urls.add(raw_url)
            target.append(item)

    async def _call_server_tool(
        self,
        *,
        query: str,
        from_dt: datetime,
        to_dt: datetime,
        limit: int,
        broad_topic: bool = False,
        topic_kind: str | None = None,
    ) -> dict[str, Any]:
        if self._native_news_agent_enabled:
            system_prompt = (
                "You are a strict news editor and web-search agent. Use web search to find current, specific news articles. "
                "Do not behave like a generic search engine. Judge every candidate before returning it. "
                "Reject homepages, category pages, support/FAQ pages, buyer guides, reviews, price pages, stock quote pages, old archive pages, and weak aggregators unless there is no better source. "
                "Keep one semantic vertical per topic; do not mix unrelated meanings of ambiguous names. "
                "Return JSON only, with no markdown."
            )
            user_prompt = (
                f"Search query: {query}\n"
                f"Detected topic type: {topic_kind or ('broad/general' if broad_topic else 'specific')}\n"
                f"Freshness target start: {from_dt.isoformat()}\n"
                f"Freshness target end: {to_dt.isoformat()}\n"
                f"Return up to {min(limit, self._native_judge_max_candidates)} candidates in this exact JSON shape:\n"
                "{\n"
                "  \"candidates\": [\n"
                "    {\n"
                "      \"title\": \"article title\",\n"
                "      \"url\": \"https://...\",\n"
                "      \"source\": \"source/domain\",\n"
                "      \"published_at\": \"ISO-8601 date if visible, else null\",\n"
                "      \"summary\": \"one sentence\",\n"
                "      \"is_news_article\": true,\n"
                "      \"is_fresh\": true,\n"
                "      \"topic_match\": 0.0,\n"
                "      \"source_quality\": \"tier1|strong_niche|standard|weak|blocked\",\n"
                "      \"reject_reason\": null\n"
                "    }\n"
                "  ]\n"
                "}\n"
                "Rules: topic_match must be 0..1. Return only specific article URLs. "
                "If a candidate is not a real current news article, set is_news_article=false and reject_reason. "
                "Prefer authoritative or strong niche sources over weak aggregators."
            )
        else:
            system_prompt = (
                "You are a news discovery assistant. Search the web for current news article candidates for the given search query. "
                "Prefer authoritative journalism, official reports, and pages that look like specific articles. Avoid old archive articles, "
                "evergreen pages, stale explainers, homepages, category pages and generic news hubs. Do not return zero solely because "
                "a publication date is not visible in the search result; local validation will verify dates and reject stale items."
            )
            user_prompt = (
                f"Search query: {query}\n"
                f"Detected topic type: {topic_kind or ('broad/general' if broad_topic else 'specific')}\n"
                f"Target freshness window start: {from_dt.isoformat()}\n"
                f"Target freshness window end: {to_dt.isoformat()}\n"
                f"Return up to {limit} specific article links that are likely to be current/recent. "
                "Prefer visible publication dates, but include strong article candidates even when the date is not shown in the search result. "
                "Use short one-line reasons. Exclude homepages, encyclopedias, non-news explainers, organization landing pages, category pages, old archive pages, reviews, buyer guides, stock-analysis pages, price pages, and generic news-hub pages."
            )
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "top_p": 0.2,
            "tools": [
                {
                    "type": "openrouter:web_search",
                    "parameters": {
                        "max_results": limit,
                        "max_total_results": limit,
                        "search_context_size": "low",
                    },
                }
            ],
        }
        if self._native_news_agent_enabled:
            body["response_format"] = {"type": "json_object"}
        estimate = self._estimated_search_call_cost(limit)
        label = "openrouter.web_search.native" if self._native_news_agent_enabled else "openrouter.web_search.raw"
        try:
            if self._budget is not None:
                self._budget.require_spend(label, estimate, reserve_after_usd=self._reserved_llm_budget_usd)
        except BudgetExhausted:
            logger.info(
                "source_fetch_budget_exhausted",
                source=self.name,
                label=label,
                query=query,
                estimated_cost_usd=estimate,
                spent_usd=self._budget.spent_usd if self._budget is not None else None,
                hard_limit_usd=self._budget.hard_limit_usd if self._budget is not None else None,
            )
            return {"choices": [{"message": {"content": "{\"candidates\": []}"}}]}
        payload = await self._post_chat_completions(body)
        if self._budget is not None:
            self._budget.record_call(
                label=label,
                estimated_cost_usd=estimate,
                payload=payload,
                metadata={"query": query, "limit": limit, "topic_kind": topic_kind},
            )
        return payload

    async def _call_plugin_fallback(
        self,
        *,
        query: str,
        from_dt: datetime,
        to_dt: datetime,
        limit: int,
    ) -> dict[str, Any]:
        body = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a news discovery assistant. Find current news article candidates for the given query. "
                        "Prefer authoritative sources with visible publication dates and cite each result. Avoid generic hubs and old archive pages."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Search query: {query}\n"
                        "Detected topic type: legacy_fallback\n"
                        f"Target freshness window start: {from_dt.isoformat()}\n"
                        f"Target freshness window end: {to_dt.isoformat()}\n"
                        f"Return up to {limit} specific article links that are likely to be current/recent. "
                        "Prefer visible publication dates, but include strong article candidates even when the date is not shown in the search result. "
                        "Avoid homepages, encyclopedias, non-news explainers, organization landing pages, category pages, old archive pages, stock-analysis pages, and generic news-hub pages."
                    ),
                },
            ],
            "temperature": 0,
            "top_p": 0.2,
            "plugins": [{"id": "web", "max_results": limit}],
        }
        estimate = self._estimated_search_call_cost(limit)
        label = "openrouter.web_search.plugin_fallback"
        try:
            if self._budget is not None:
                self._budget.require_spend(label, estimate, reserve_after_usd=self._reserved_llm_budget_usd)
        except BudgetExhausted:
            logger.info(
                "source_fetch_budget_exhausted",
                source=self.name,
                label=label,
                query=query,
                estimated_cost_usd=estimate,
                spent_usd=self._budget.spent_usd if self._budget is not None else None,
                hard_limit_usd=self._budget.hard_limit_usd if self._budget is not None else None,
            )
            return {"choices": [{"message": {"content": ""}}]}
        payload = await self._post_chat_completions(body)
        if self._budget is not None:
            self._budget.record_call(
                label=label,
                estimated_cost_usd=estimate,
                payload=payload,
                metadata={"query": query, "limit": limit},
            )
        return payload

    async def _post_chat_completions(self, body: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            return response.json()

    def _extract_native_items_from_message(self, message: dict[str, Any], limit: int) -> list[RawSourceItem]:
        if not self._native_news_agent_enabled:
            return []
        parsed = self._parse_native_json(self._flatten_content(message.get("content", "")))
        candidates = parsed.get("candidates") if isinstance(parsed, dict) else None
        if not isinstance(candidates, list):
            return []
        items: list[RawSourceItem] = []
        for candidate in candidates[: max(limit, self._native_judge_max_candidates)]:
            if not isinstance(candidate, dict):
                continue
            raw_url = str(candidate.get("url") or "").strip()
            if not raw_url:
                continue
            parsed_url = self._safe_http_url(raw_url)
            if parsed_url is None:
                continue
            if not self._native_candidate_usable(candidate):
                continue
            title = str(candidate.get("title") or self._title_from_url(raw_url)).strip()[:240]
            summary = str(candidate.get("summary") or candidate.get("description") or "").strip() or None
            source_name = str(candidate.get("source") or urlparse(raw_url).netloc.replace("www.", "")).strip()
            published_at = self._parse_candidate_datetime(candidate.get("published_at"))
            metadata = {
                "native_judge": True,
                "native_topic_match": self._float_or_none(candidate.get("topic_match")),
                "native_source_quality": str(candidate.get("source_quality") or "").lower() or None,
                "native_reject_reason": candidate.get("reject_reason"),
                "native_is_fresh": candidate.get("is_fresh"),
                "native_is_news_article": candidate.get("is_news_article"),
                "search_annotation": True,
                "search_snippet": bool(summary),
            }
            if published_at is not None:
                metadata["published_at_source"] = "openrouter_native"
            items.append(
                RawSourceItem(
                    source_type=self.source_type,
                    provider=self.name,
                    url=parsed_url,
                    title=title,
                    description=summary,
                    source_name=source_name or urlparse(raw_url).netloc.replace("www.", ""),
                    source_language=None,
                    published_at=published_at,
                    metadata=metadata,
                )
            )
            if len(items) >= limit:
                break
        return items

    def _native_candidate_usable(self, candidate: dict[str, Any]) -> bool:
        if candidate.get("is_news_article") is False:
            return False
        reject_reason = candidate.get("reject_reason")
        if reject_reason not in (None, "", False):
            return False
        topic_match = self._float_or_none(candidate.get("topic_match"))
        if topic_match is not None and topic_match < self._native_judge_min_topic_match:
            return False
        source_quality = str(candidate.get("source_quality") or "").lower().strip()
        if self._native_reject_weak_sources and source_quality in {"blocked", "spam", "irrelevant"}:
            return False
        return True

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _parse_candidate_datetime(value: Any) -> datetime | None:
        if value in (None, "", False):
            return None
        return OpenRouterWebSearchSource._parse_datetime(str(value).strip())

    @staticmethod
    def _parse_native_json(text: str) -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {}
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"\s*```$", "", text).strip()
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    def _extract_items_from_payload(self, payload: dict[str, Any], limit: int) -> list[RawSourceItem]:
        message = payload.get("choices", [{}])[0].get("message", {})
        annotations = message.get("annotations") or []
        items: list[RawSourceItem] = []
        seen_urls: set[str] = set()

        for native_item in self._extract_native_items_from_message(message, limit):
            raw_url = str(native_item.url) if native_item.url is not None else None
            if not raw_url or raw_url in seen_urls:
                continue
            seen_urls.add(raw_url)
            items.append(native_item)
            if len(items) >= limit:
                return items

        for ann in annotations:
            citation = ann.get("url_citation") or {}
            raw_url = citation.get("url")
            if not raw_url or raw_url in seen_urls:
                continue
            parsed_url = self._safe_http_url(raw_url)
            if parsed_url is None:
                continue
            seen_urls.add(raw_url)
            title = (citation.get("title") or self._title_from_url(raw_url)).strip()
            if not self._looks_like_basic_link_candidate(raw_url, title):
                continue
            snippet = (citation.get("content") or "").strip() or None
            source_name = urlparse(raw_url).netloc.replace("www.", "")
            items.append(
                RawSourceItem(
                    source_type=self.source_type,
                    provider=self.name,
                    url=parsed_url,
                    title=title,
                    description=snippet,
                    source_name=source_name,
                    source_language=None,
                    published_at=None,
                    metadata={"search_annotation": True, "search_snippet": bool(snippet)},
                )
            )
            if len(items) >= limit:
                return items

        content = message.get("content", "")
        text_content = self._flatten_content(content)
        for raw_url in _URL_RE.findall(text_content):
            raw_url = raw_url.rstrip(".,]")
            if raw_url in seen_urls:
                continue
            parsed_url = self._safe_http_url(raw_url)
            if parsed_url is None:
                continue
            seen_urls.add(raw_url)
            source_name = urlparse(raw_url).netloc.replace("www.", "")
            items.append(
                RawSourceItem(
                    source_type=self.source_type,
                    provider=self.name,
                    url=parsed_url,
                    title=self._title_from_url(raw_url),
                    description=None,
                    source_name=source_name,
                    source_language=None,
                    published_at=None,
                )
            )
            if len(items) >= limit:
                break
        return items



    async def _enrich_and_filter_recent(
        self,
        items: list[RawSourceItem],
        *,
        from_dt: datetime,
        to_dt: datetime,
        plan,
        allow_search_snippet_fallback: bool = False,
        record: SearchRunRecord | None = None,
        pass_index: int | None = None,
        query_text: str | None = None,
    ) -> list[RawSourceItem]:
        """Enrich links and run the v6 balanced candidate decision layer.

        v5.x rejected candidates too early: missing metadata date, 8-day-old verified
        article, or generic suffixes such as "TEAM" could all zero out a topic. v6
        keeps hard rejects for hubs/wrong entity/old content, but lets high-directness
        search annotations through as weak-but-usable candidates.
        """
        enriched: list[RawSourceItem] = []
        async with httpx.AsyncClient(timeout=min(self._timeout_seconds, 15.0), follow_redirects=True) as client:
            for item in items:
                url = str(item.url) if item.url is not None else None
                if not url:
                    continue

                try:
                    response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    if response.status_code >= 400:
                        fallback = self._fallback_candidate(
                            item,
                            from_dt=from_dt,
                            to_dt=to_dt,
                            plan=plan,
                            reason=f"http_{response.status_code}",
                            allow_search_snippet_fallback=True,
                            record=record,
                            pass_index=pass_index,
                            query_text=query_text,
                        )
                        if fallback is not None:
                            enriched.append(fallback)
                        continue
                except Exception as exc:
                    fallback = self._fallback_candidate(
                        item,
                        from_dt=from_dt,
                        to_dt=to_dt,
                        plan=plan,
                        reason=type(exc).__name__,
                        allow_search_snippet_fallback=True,
                        record=record,
                        pass_index=pass_index,
                        query_text=query_text,
                    )
                    if fallback is not None:
                        enriched.append(fallback)
                    continue

                meta = extract_html_metadata(response.text)
                canonical_url = meta.canonical_url or self._extract_canonical_url(response.text) or str(response.url)
                candidate_title = meta.title or item.title
                candidate_desc = meta.description or item.description
                source_language = item.source_language or meta.language or self._extract_language(response.text)
                parsed_url = self._safe_http_url(canonical_url)
                if parsed_url is None or not self._looks_like_news_article(canonical_url, candidate_title, plan=plan):
                    self._log_rejection(plan, canonical_url, candidate_title, candidate_desc, "url_does_not_look_like_news_article")
                    continue

                published_at, published_source = self._extract_best_publish_datetime(
                    html=response.text,
                    canonical_url=canonical_url,
                    last_modified=response.headers.get("last-modified"),
                )
                if published_at is None and item.published_at is not None:
                    published_at = item.published_at
                    published_source = str(item.metadata.get("published_at_source") or "openrouter_native")
                decision = evaluate_candidate(
                    plan,
                    url=canonical_url,
                    title=candidate_title,
                    description=candidate_desc,
                    published_at=published_at,
                    published_at_source=published_source,
                    to_dt=to_dt,
                    policy=self._freshness_policy,
                    search_annotation=bool(item.metadata.get("search_annotation")),
                    search_snippet=bool(item.metadata.get("search_snippet")),
                    source_name=item.source_name,
                )
                if not decision.usable:
                    event = self._log_decision(plan, canonical_url, candidate_title, candidate_desc, decision, pass_index=pass_index, query_text=query_text)
                    if record is not None and event is not None:
                        record.add_decision(event)
                    continue

                event = self._log_decision(plan, canonical_url, candidate_title, candidate_desc, decision, pass_index=pass_index, query_text=query_text)
                if record is not None and event is not None:
                    record.add_decision(event)
                enriched.append(item.model_copy(update={
                    "url": parsed_url,
                    "title": candidate_title,
                    "description": candidate_desc,
                    "published_at": decision.published_at or to_dt,
                    "source_language": source_language,
                    "metadata": {
                        **item.metadata,
                        "canonical_url": canonical_url,
                        "topic_match_score": decision.score,
                        "directness_score": decision.directness_score,
                        "article_confidence": decision.article_confidence,
                        "candidate_status": decision.status.value,
                        "quality_reason": decision.reason,
                        "published_at_source": decision.published_at_source,
                        "freshness_verified": decision.freshness_verified,
                        "source_weight": source_quality_weight(item.source_name, plan.topic_kind),
                        "authority_tier": source_authority_tier(item.source_name, plan.topic_kind),
                        "topic_kind": plan.topic_kind,
                        "native_judge": item.metadata.get("native_judge"),
                        "native_topic_match": item.metadata.get("native_topic_match"),
                        "native_source_quality": item.metadata.get("native_source_quality"),
                        "native_reject_reason": item.metadata.get("native_reject_reason"),
                        **decision.metadata,
                    },
                }))
        enriched.sort(key=lambda x: (int(x.metadata.get("candidate_status") == "accepted"), float(x.metadata.get("source_weight", source_quality_weight(x.source_name, str(x.metadata.get("topic_kind", ""))))), int(x.metadata.get("directness_score", 0)), int(x.metadata.get("topic_match_score", 0)), x.published_at), reverse=True)
        return enriched

    def _fallback_candidate(
        self,
        item: RawSourceItem,
        *,
        from_dt: datetime,
        to_dt: datetime,
        plan,
        reason: str,
        allow_search_snippet_fallback: bool = False,
        record: SearchRunRecord | None = None,
        pass_index: int | None = None,
        query_text: str | None = None,
    ) -> RawSourceItem | None:
        url = str(item.url) if item.url is not None else None
        if not url:
            return None
        if not self._looks_like_news_article(url, item.title, plan=plan):
            self._log_rejection(plan, url, item.title, item.description, f"fallback_not_article:{reason}")
            return None

        url_date = self._extract_date_from_url(url)
        published_at = url_date or item.published_at
        published_source = "url" if url_date is not None else (str(item.metadata.get("published_at_source")) if item.published_at is not None else None)
        decision = evaluate_candidate(
            plan,
            url=url,
            title=item.title,
            description=item.description,
            published_at=published_at,
            published_at_source=published_source,
            to_dt=to_dt,
            policy=self._freshness_policy,
            search_annotation=bool(item.metadata.get("search_annotation")) and (allow_search_snippet_fallback or self._allow_search_snippet_fallback),
            search_snippet=bool(item.metadata.get("search_snippet")) and (allow_search_snippet_fallback or self._allow_search_snippet_fallback),
            source_name=item.source_name,
        )
        if not decision.usable:
            event = self._log_decision(plan, url, item.title, item.description, decision, prefix=f"fallback:{reason}", pass_index=pass_index, query_text=query_text)
            if record is not None and event is not None:
                record.add_decision(event)
            return None
        event = self._log_decision(plan, url, item.title, item.description, decision, prefix=f"fallback:{reason}", pass_index=pass_index, query_text=query_text)
        if record is not None and event is not None:
            record.add_decision(event)
        return item.model_copy(update={
            "published_at": decision.published_at or to_dt,
            "metadata": {
                **item.metadata,
                "canonical_url": url,
                "topic_match_score": decision.score,
                "directness_score": decision.directness_score,
                "article_confidence": decision.article_confidence,
                "metadata_fallback": True,
                "metadata_fallback_reason": reason,
                "candidate_status": decision.status.value,
                "quality_reason": decision.reason,
                "published_at_source": decision.published_at_source,
                "freshness_verified": decision.freshness_verified,
                "source_weight": source_quality_weight(item.source_name, plan.topic_kind),
                "authority_tier": source_authority_tier(item.source_name, plan.topic_kind),
                "topic_kind": plan.topic_kind,
                **decision.metadata,
            },
        })


    @staticmethod
    def _is_before_freshness_floor(published_at: datetime, freshness_floor: datetime, published_source: str | None) -> bool:
        # Dates extracted from URLs usually have day precision only. Treat the whole
        # calendar day as inside the window, otherwise a URL like /2026/04/26/...
        # is wrongly rejected at 12:00 on 2026-04-26.
        if published_source == "url" and published_at.date() == freshness_floor.date():
            return False
        return published_at < freshness_floor

    def _freshness_floor(self, *, from_dt: datetime, to_dt: datetime, plan) -> datetime:
        floor = from_dt
        max_age_floor = to_dt - timedelta(hours=self._max_article_age_hours)
        if max_age_floor > floor:
            floor = max_age_floor
        # Follow-up runs should be stricter, because sending stale leftovers as "latest" feels broken.
        if not getattr(plan, "first_run", False):
            followup_floor = to_dt - timedelta(hours=min(48, self._max_article_age_hours))
            if followup_floor > floor:
                floor = followup_floor
        if floor.tzinfo is None:
            floor = floor.replace(tzinfo=timezone.utc)
        return floor.astimezone(timezone.utc)

    def _extract_best_publish_datetime(
        self,
        *,
        html: str,
        canonical_url: str,
        last_modified: str | None,
    ) -> tuple[datetime | None, str | None]:
        published_at = self._extract_published_at(html)
        if published_at is not None:
            return published_at, "metadata"

        published_at = self._extract_date_from_url(canonical_url)
        if published_at is not None:
            return published_at, "url"

        if not self._require_verified_publish_date or self._allow_weak_publish_dates:
            published_at = self._extract_last_modified(last_modified)
            if published_at is not None:
                return published_at, "last_modified"

        return None, None

    def _log_rejection(self, plan, url: str, title: str | None, description: str | None, reason: str) -> None:
        if not self._debug_rejections:
            return
        quality = candidate_quality(plan, url=url, title=title, description=description)
        logger.info(
            "candidate_rejected",
            source=self.name,
            topic=plan.normalized_query,
            topic_kind=plan.topic_kind,
            reason=reason,
            quality_reason=quality.reason,
            score=quality.score,
            directness_score=quality.directness_score,
            url=url,
            title=title,
        )

    def _log_decision(
        self,
        plan,
        url: str,
        title: str | None,
        description: str | None,
        decision,
        prefix: str | None = None,
        pass_index: int | None = None,
        query_text: str | None = None,
    ) -> dict[str, Any]:
        reason = f"{prefix}:{decision.reason}" if prefix else decision.reason
        event = decision_event_from_candidate(
            source=self.name,
            topic=plan.normalized_query,
            topic_kind=plan.topic_kind,
            status=decision.status.value,
            reason=reason,
            score=decision.score,
            directness_score=decision.directness_score,
            article_confidence=decision.article_confidence,
            freshness_verified=decision.freshness_verified,
            published_at_source=decision.published_at_source,
            published_at=decision.published_at,
            age_hours=candidate_age_hours(decision.published_at),
            url=url,
            title=title,
            pass_index=pass_index,
            query=query_text,
        )
        event["source_weight"] = decision.metadata.get("source_weight")
        event["authority_tier"] = decision.metadata.get("authority_tier")
        if self._debug_rejections:
            logger.info("candidate_decision", **event)
        return event

    @staticmethod
    def _extract_canonical_url(html: str) -> str | None:
        patterns = [
            r"<link[^>]+rel=[\"']canonical[\"'][^>]+href=[\"']([^\"']+)[\"']",
            r"<meta[^>]+property=[\"']og:url[\"'][^>]+content=[\"']([^\"']+)[\"']",
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _extract_language(html: str) -> str | None:
        for pattern in [r"<html[^>]+lang=[\"']([a-zA-Z-]+)[\"']", r"<meta[^>]+property=[\"']og:locale[\"'][^>]+content=[\"']([a-zA-Z_]+)[\"']"]:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).split('_')[0].split('-')[0].lower()
        return None

    @staticmethod
    def _extract_published_at(html: str) -> datetime | None:
        patterns = [
            r"<meta[^>]+property=[\"']article:published_time[\"'][^>]+content=[\"']([^\"']+)[\"']",
            r"<meta[^>]+name=[\"']article:published_time[\"'][^>]+content=[\"']([^\"']+)[\"']",
            r"<meta[^>]+name=[\"']parsely-pub-date[\"'][^>]+content=[\"']([^\"']+)[\"']",
            r"<meta[^>]+name=[\"']pubdate[\"'][^>]+content=[\"']([^\"']+)[\"']",
            r"<time[^>]+datetime=[\"']([^\"']+)[\"']",
            r'"datePublished"\s*:\s*"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if not match:
                continue
            dt = OpenRouterWebSearchSource._parse_datetime(match.group(1).strip())
            if dt is not None:
                return dt
        return None


    @staticmethod
    def _extract_last_modified(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            dt = parsedate_to_datetime(value)
        except Exception:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def _extract_date_from_url(raw_url: str) -> datetime | None:
        path = urlparse(raw_url).path
        patterns = [
            r'/(20\d{2})/(\d{1,2})/(\d{1,2})/',
            r'/(\d{1,2})[.-](\d{1,2})[.-](20\d{2})/',
        ]
        for pattern in patterns:
            match = re.search(pattern, path)
            if not match:
                continue
            groups = match.groups()
            try:
                if len(groups[0]) == 4:
                    year, month, day = map(int, groups)
                else:
                    day, month, year = map(int, groups)
                return datetime(year, month, day, tzinfo=timezone.utc)
            except Exception:
                continue
        return None

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            pass
        try:
            return parsedate_to_datetime(value)
        except Exception:
            return None

    @staticmethod
    def _looks_like_basic_link_candidate(raw_url: str, title: str | None) -> bool:
        parsed = urlparse(raw_url)
        host = parsed.netloc.lower().replace("www.", "")
        path = parsed.path.lower()
        title_norm = (title or "").lower()

        if host in _HOST_BLOCKLIST or any(h in host for h in _NON_NEWS_HOST_HINTS):
            return False
        if any(marker in title_norm for marker in _TITLE_BLOCK_HINTS):
            return False
        if _looks_like_news_hub_title(title, path):
            return False
        if any(marker in path for marker in (
            '/video/', '/videos/', '/watch/', '/watch?', '/podcast', '/audio/',
            '/gallery/', '/galleries/', '/photos/', '/opinion/', '/tag/', '/tags/',
            '/topic/', '/topics/', '/category/', '/categories/', '/archive', '/archives',
            '/all', '/latest'
        )):
            return False
        return True

    @staticmethod
    def _looks_like_news_article(raw_url: str, title: str | None, *, plan=None) -> bool:
        parsed = urlparse(raw_url)
        host = parsed.netloc.lower().replace("www.", "")
        path = parsed.path.lower()
        title_norm = (title or "").lower()

        if not OpenRouterWebSearchSource._looks_like_basic_link_candidate(raw_url, title):
            return False
        if ('latest news' in title_norm or 'news today' in title_norm or 'headlines' in title_norm) and path.rstrip('/') in {'/news','/latest','/latest-news','/world','/business','/politics','/markets','/sport','/sports'}:
            return False
        if host.endswith('.org') and not any(marker in path for marker in ('/news', '/article', '/articles', '/stories', '/story', '/press', '/press-release')):
            return False
        if len(path.rstrip('/').split('/')) < 2 and not any(h in path for h in _NEWS_PATH_HINTS):
            return False
        if not any(h in path for h in _NEWS_PATH_HINTS) and not re.search(r'/20\d{2}/', path):
            trusted = ('reuters', 'apnews', 'bbc', 'dw', 'ft.com', 'wsj', 'nytimes', 'theguardian', 'sky', 'bloomberg')
            if any(t in host for t in trusted):
                return True
            # Many legitimate article URLs do not use /news/YYYY URL shapes.
            # Let the topical quality gate decide when the title is direct enough.
            if plan is not None and getattr(plan, "topic_kind", "") in {"technology", "esports", "game_updates", "entertainment", "entertainment_company", "team_org", "sports_team", "brand_company", "business", "person", "city", "country", "crypto", "broad_single", "broad_dual", "ambiguous_acronym"}:
                if title_norm and len(re.findall(r"[a-zA-Z0-9а-яА-ЯёЁіІїЇєЄґҐ]+", title_norm)) >= 4:
                    return True
            return False
        return True

    @staticmethod
    def _flatten_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    parts.append(str(part.get("text", "")))
                else:
                    parts.append(str(part))
            return "".join(parts)
        return str(content)

    @staticmethod
    def _safe_http_url(raw_url: str) -> HttpUrl | None:
        try:
            return _HTTP_URL.validate_python(raw_url)
        except Exception:
            return None

    @staticmethod
    def _title_from_url(raw_url: str) -> str:
        parsed = urlparse(raw_url)
        tail = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
        candidate = tail.replace("-", " ").replace("_", " ").strip()
        return candidate[:160] or parsed.netloc
