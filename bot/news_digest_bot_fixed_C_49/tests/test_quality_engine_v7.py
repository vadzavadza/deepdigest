from datetime import datetime, timedelta, timezone

from app.search_v2.strategy import build_search_plan, canonicalize_topic, classify_topic
from app.search_v2.source_quality import source_quality_weight, source_vertical_mismatch


def _plan(topic: str):
    now = datetime.now(tz=timezone.utc)
    return build_search_plan(topic, from_dt=now - timedelta(days=7), to_dt=now, first_run=True)


def test_v7_entity_aliases_keep_common_ambiguous_inputs_out_of_broad_single():
    assert canonicalize_topic("вашингтон") == "washington"
    assert classify_topic("вашингтон") == "ambiguous_geo"
    assert classify_topic("navi") == "team_org"
    assert classify_topic("NAVI TEAM") == "team_org"


def test_v7_query_planner_uses_vertical_context_for_team_and_geo():
    navi = _plan("navi")
    assert navi.topic_kind == "team_org"
    joined = " ".join(navi.query_variants).lower()
    assert "roster" in joined or "official team" in joined

    washington = _plan("вашингтон")
    assert washington.topic_kind == "ambiguous_geo"
    joined_w = " ".join(washington.query_variants).lower()
    assert "washington dc" in joined_w or "washington state" in joined_w


def test_v7_vertical_source_quality_rejects_finance_for_esports():
    assert source_vertical_mismatch("marketbeat.com", "team_org") is True
    assert source_quality_weight("marketbeat.com", "team_org") < -20
    assert source_vertical_mismatch("esports.gg", "team_org") is False
    assert source_quality_weight("esports.gg", "team_org") >= 16


def test_v7_brand_sources_penalize_weak_aggregators():
    assert source_quality_weight("antigua.news", "brand_company") < 0
    assert source_quality_weight("pressroom.toyota.com", "brand_company") >= 16
