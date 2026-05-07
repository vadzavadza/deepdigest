from __future__ import annotations

import json
from datetime import datetime, timezone

from app.search_v2.recorder import SearchRunRecorder, decision_event_from_candidate
from app.tools.replay_search_run import analyze_run, grade_run, render_markdown
from app.schemas.sources import RawSourceItem
from app.domain.enums import SourceType


def test_search_run_recorder_writes_replayable_json(tmp_path):
    recorder = SearchRunRecorder(enabled=True, directory=tmp_path)
    now = datetime(2026, 4, 27, tzinfo=timezone.utc)
    record = recorder.start(
        topic="bitcoin",
        normalized_topic="bitcoin",
        topic_kind="crypto",
        from_dt=now,
        to_dt=now,
        query_variants=["bitcoin latest news"],
        settings={"budget_usd": 0.07},
    )
    assert record is not None
    raw = RawSourceItem(
        source_type=SourceType.WEB_SEARCH,
        provider="openrouter_web_search",
        url="https://example.com/news/2026/04/27/bitcoin-test",
        title="Bitcoin test news",
        description="A direct bitcoin test story",
        source_name="example.com",
        published_at=None,
        metadata={"search_annotation": True},
    )
    record.add_pass(pass_index=1, query="bitcoin latest news", raw_items=[raw], accepted_count=1, merged_count=1)
    record.add_decision(
        decision_event_from_candidate(
            source="openrouter_web_search",
            topic="bitcoin",
            topic_kind="crypto",
            status="accepted",
            reason="accepted_verified",
            score=30,
            directness_score=25,
            article_confidence=5,
            freshness_verified=True,
            published_at=now,
            published_at_source="metadata",
            age_hours=0.0,
            url="https://example.com/news/2026/04/27/bitcoin-test",
            title="Bitcoin test news",
            pass_index=1,
            query="bitcoin latest news",
        )
    )
    record.finish(status="success", final_items=[raw])
    path = recorder.write(record)
    assert path is not None and path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "search_run_v1"
    assert data["summary"]["raw_count"] == 1
    assert data["summary"]["final_count"] == 1


def test_replay_analysis_grades_filter_failure():
    data = {
        "run_id": "r1",
        "topic": "Kyiv",
        "topic_kind": "city",
        "status": "empty",
        "raw_candidates": [{"url": "https://example.com/a", "source_name": "example.com"}],
        "candidate_decisions": [
            {"status": "rejected", "reason": "missing_publish_date_not_usable", "domain": "example.com"}
        ],
        "final_items": [],
    }
    summary = analyze_run(data)
    grade, notes = grade_run(summary)
    assert grade == "retrieval_ok_filter_failed"
    assert "filter_or_selection_zeroed_results" in notes
    assert "missing_publish_date_not_usable" in render_markdown([summary])
