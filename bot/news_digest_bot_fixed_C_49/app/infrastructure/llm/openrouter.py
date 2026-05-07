from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import BaseModel

from app.domain.enums import OutputLanguage
from app.infrastructure.llm.base import LLMProvider
from app.schemas.llm import (
    RelevanceCheckResult,
    SemanticDuplicateResult,
    SummaryResult,
    TranslationResult,
)
from app.schemas.sources import NormalizedSourceItem, StoryCandidate
from app.shared.cost_budget import BudgetExhausted, CostBudget
from app.shared.logging import get_logger
from app.shared.settings import get_settings

logger = get_logger(__name__)


class OpenRouterProvider(LLMProvider):
    def __init__(
        self,
        *,
        model: str | None = None,
        timeout_seconds: float = 30.0,
        budget: CostBudget | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._api_key = settings.openrouter_api_key
        self._model = model or settings.openrouter_default_model
        self._timeout_seconds = timeout_seconds
        self._budget = budget
        self._relevance_estimated_cost_usd = max(settings.openrouter_llm_relevance_estimated_cost_usd, 0.0)
        self._summary_estimated_cost_usd = max(settings.openrouter_llm_summary_estimated_cost_usd, 0.0)
        self._translation_estimated_cost_usd = max(settings.openrouter_llm_translation_estimated_cost_usd, 0.0)

    def attach_budget(self, budget: CostBudget | None) -> None:
        self._budget = budget

    async def check_relevance(
        self,
        *,
        topic_query: str,
        article: NormalizedSourceItem,
    ) -> RelevanceCheckResult:
        return await self._structured_request(
            schema=RelevanceCheckResult,
            system_prompt=(
                "You are a news relevance classifier. Use only the given source item fields. "
                "Do not invent facts. Return valid JSON only."
            ),
            user_payload={
                "topic_query": topic_query,
                "source_item": article.model_dump(mode="json"),
                "task": "Return relevance as relevant, weak or reject.",
            },
        )

    async def summarize_article(
        self,
        *,
        topic_query: str,
        article: NormalizedSourceItem,
    ) -> SummaryResult:
        return await self._structured_request(
            schema=SummaryResult,
            system_prompt=(
                "You summarize news items. Use only the provided fields. "
                "Do not invent facts. Keep factual neutrality. Return valid JSON only."
            ),
            user_payload={
                "topic_query": topic_query,
                "source_item": article.model_dump(mode="json"),
                "task": "Write a concise 2-3 sentence summary.",
            },
        )

    async def translate_text(
        self,
        *,
        text: str,
        target_language: OutputLanguage,
    ) -> TranslationResult:
        return await self._structured_request(
            schema=TranslationResult,
            system_prompt=(
                "You translate short news summaries while preserving meaning and neutral tone. "
                "Return valid JSON only."
            ),
            user_payload={
                "text": text,
                "target_language": target_language.value,
            },
        )

    async def semantic_duplicate_check(
        self,
        *,
        left: StoryCandidate,
        right: StoryCandidate,
    ) -> SemanticDuplicateResult:
        return await self._structured_request(
            schema=SemanticDuplicateResult,
            system_prompt=(
                "You compare two news story candidates. Determine whether they describe the same "
                "business event. Return valid JSON only."
            ),
            user_payload={
                "left": left.model_dump(mode="json"),
                "right": right.model_dump(mode="json"),
            },
        )

    def _estimate_for_schema(self, schema: type[BaseModel]) -> float:
        if schema is RelevanceCheckResult:
            return self._relevance_estimated_cost_usd
        if schema is SummaryResult:
            return self._summary_estimated_cost_usd
        if schema is TranslationResult:
            return self._translation_estimated_cost_usd
        return max(self._relevance_estimated_cost_usd, self._summary_estimated_cost_usd)

    async def _structured_request(
        self,
        *,
        schema: type[BaseModel],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> BaseModel:
        url = f"{self._base_url}/chat/completions"
        label = f"openrouter.llm.{schema.__name__}"
        estimate = self._estimate_for_schema(schema)
        try:
            if self._budget is not None:
                self._budget.require_spend(label, estimate)
        except BudgetExhausted:
            logger.info(
                "llm_budget_exhausted",
                schema=schema.__name__,
                estimated_cost_usd=estimate,
                spent_usd=self._budget.spent_usd if self._budget is not None else None,
                hard_limit_usd=self._budget.hard_limit_usd if self._budget is not None else None,
            )
            raise

        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()

        if self._budget is not None:
            self._budget.record_call(
                label=label,
                estimated_cost_usd=estimate,
                payload=payload,
                metadata={"schema": schema.__name__, "model": self._model},
            )

        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, list):
            text_content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        else:
            text_content = str(content)

        try:
            return schema.model_validate_json(text_content)
        except Exception:
            logger.warning("llm_parse_failed", schema=schema.__name__, raw_content=text_content)
            raise
