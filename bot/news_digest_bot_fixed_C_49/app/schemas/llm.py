from pydantic import BaseModel, Field

from app.domain.enums import RelevanceLabel


class RelevanceCheckResult(BaseModel):
    relevance: RelevanceLabel
    reason: str | None = None


class SemanticDuplicateResult(BaseModel):
    same_story: bool
    confidence: float = Field(ge=0, le=1)


class SummaryResult(BaseModel):
    summary: str = Field(min_length=10, max_length=1500)


class TranslationResult(BaseModel):
    translated_text: str = Field(min_length=1, max_length=1500)
