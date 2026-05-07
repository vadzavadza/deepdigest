from typing import Protocol

from app.domain.enums import OutputLanguage
from app.schemas.llm import (
    RelevanceCheckResult,
    SemanticDuplicateResult,
    SummaryResult,
    TranslationResult,
)
from app.schemas.sources import NormalizedSourceItem, StoryCandidate


class LLMProvider(Protocol):
    async def check_relevance(
        self,
        *,
        topic_query: str,
        article: NormalizedSourceItem,
    ) -> RelevanceCheckResult:
        ...

    async def summarize_article(
        self,
        *,
        topic_query: str,
        article: NormalizedSourceItem,
    ) -> SummaryResult:
        ...

    async def translate_text(
        self,
        *,
        text: str,
        target_language: OutputLanguage,
    ) -> TranslationResult:
        ...

    async def semantic_duplicate_check(
        self,
        *,
        left: StoryCandidate,
        right: StoryCandidate,
    ) -> SemanticDuplicateResult:
        ...
