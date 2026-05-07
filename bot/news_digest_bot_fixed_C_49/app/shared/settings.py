from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    bot_token: str = Field(alias="BOT_TOKEN")
    webhook_base_url: str | None = None
    webhook_secret_token: str | None = None

    database_url: str
    redis_url: str | None = None

    openrouter_api_key: str = Field(alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "openai/gpt-4.1-mini"
    openrouter_search_model: str | None = None
    openrouter_web_search_max_results: int = 15
    # v7: soft target is the normal cost target; hard cap is the absolute ceiling.
    news_topic_soft_budget_usd: float = 0.07
    news_topic_hard_budget_usd: float = 0.10
    # Leave a small safety margin below the hard cap for provider-side rounding / usage lag.
    news_topic_stop_margin_usd: float = 0.005
    openrouter_reserved_llm_budget_usd: float = 0.025
    openrouter_topic_budget_usd: float = 0.10
    openrouter_search_result_cost_usd: float = 0.004
    openrouter_search_call_model_reserve_usd: float = 0.002
    openrouter_llm_relevance_estimated_cost_usd: float = 0.002
    openrouter_llm_summary_estimated_cost_usd: float = 0.003
    openrouter_llm_translation_estimated_cost_usd: float = 0.002
    openrouter_web_search_results_per_call: int = 5
    openrouter_web_search_max_calls_per_topic: int = 3
    openrouter_web_search_normal_max_calls: int = 2
    openrouter_web_search_rescue_max_calls: int = 3
    openrouter_min_quality_candidates: int = 3
    openrouter_allow_plugin_fallback: bool = False
    # v7.1: use OpenRouter as a native news agent, not only as a raw link provider.
    # The model is asked to return structured JSON candidates while using openrouter:web_search.
    openrouter_native_news_agent_enabled: bool = True
    openrouter_native_judge_min_topic_match: float = 0.62
    openrouter_native_judge_max_candidates: int = 8
    openrouter_native_reject_weak_sources: bool = True
    openrouter_debug_rejections: bool = True
    # v6: do not reject useful verified articles just because they are 8-30 days old.
    # Soft age affects ranking; hard age is the maximum retrieval safety window.
    openrouter_max_article_age_hours: int = 168
    openrouter_verified_hard_max_article_age_hours: int = 720
    openrouter_followup_hard_max_article_age_hours: int = 72
    openrouter_require_verified_publish_date: bool = True
    openrouter_allow_weak_publish_dates: bool = False
    openrouter_allow_undated_fallback: bool = False
    openrouter_future_skew_hours: int = 12
    # Rescue mode: if strict verified-date filtering returns too little, allow high-confidence
    # OpenRouter search annotations as weak-freshness candidates. These are penalized and capped.
    openrouter_allow_search_snippet_fallback: bool = True
    openrouter_search_snippet_fallback_min_directness: int = 12
    openrouter_search_snippet_fallback_min_confidence: int = 2
    openrouter_max_weak_freshness_items_per_digest: int = 1
    # v5.3: one run should perform enough adaptive search passes before giving up.
    openrouter_adaptive_target_candidates: int = 3
    openrouter_min_search_passes: int = 2
    # If the user presses "run now" again right after a digest, do not drain stale leftovers.
    immediate_repeat_guard_minutes: int = 15

    # v6.3 evaluation/replay: save raw search candidates and decisions to JSON files.
    # Use with docker-compose volume ./debug_runs:/app/debug_runs.
    search_debug_dump_enabled: bool = False
    search_debug_dump_dir: str = "debug_runs"
    search_eval_fixture_dir: str = "eval_fixtures"

    enable_openrouter_web_search_source: bool = True
    enable_mock_source: bool = False
    enable_telegram_channel_source: bool = False
    enable_rss_source: bool = False

    default_timezone: str = "Asia/Tbilisi"
    default_output_language: str = "en"
    story_memory_days: int = 7
    max_articles_per_provider: int = 100
    max_stories_per_post: int = 5
    llm_relevance_max_checks_per_topic: int = 8
    llm_skip_relevance_for_native_judged_candidates: bool = True
    llm_native_relevance_min_topic_match: float = 0.70
    publish_empty_digest: bool = False
    scheduler_refresh_seconds: int = 10
    scheduler_job_misfire_grace_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
