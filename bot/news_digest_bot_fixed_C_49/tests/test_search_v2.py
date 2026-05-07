from datetime import datetime, timedelta, timezone

from app.search_v2.article_filter import is_candidate_article, topic_match_score
from app.search_v2.strategy import build_search_plan, classify_topic


def test_classify_game_updates():
    assert classify_topic('CS2 latest updates') == 'game_updates'


def test_build_search_plan_country_queries():
    plan = build_search_plan('USA', from_dt=datetime.now(tz=timezone.utc)-timedelta(hours=24), to_dt=datetime.now(tz=timezone.utc), first_run=False)
    assert plan.topic_kind == 'country'
    assert any('politics' in q.lower() for q in plan.query_variants)


def test_section_page_rejected():
    plan = build_search_plan('usa', from_dt=datetime.now(tz=timezone.utc)-timedelta(hours=24), to_dt=datetime.now(tz=timezone.utc), first_run=False)
    assert not is_candidate_article(plan, url='https://www.theguardian.com/us-news/2026/apr/16/all', title='US politics | The Guardian', description='Latest US politics')


def test_article_with_topic_overlap_allowed():
    plan = build_search_plan('BMW', from_dt=datetime.now(tz=timezone.utc)-timedelta(days=7), to_dt=datetime.now(tz=timezone.utc), first_run=True)
    score = topic_match_score(plan, title='2027 BMW i7 gets Neue Klasse inspired facelift', description='Latest BMW 7 Series changes', url='https://example.com/2026/04/23/bmw-i7-facelift')
    assert score >= 4


def test_classify_england_as_country():
    assert classify_topic('england') == 'country'


def test_reject_news_hub_page_for_bitcoin():
    plan = build_search_plan('bitcoin', from_dt=datetime.now(tz=timezone.utc)-timedelta(days=7), to_dt=datetime.now(tz=timezone.utc), first_run=True)
    assert not is_candidate_article(plan, url='https://cryptoslate.com/news/', title='Bitcoin News Today: Latest BTC Price, Mining & Market Headlines', description='Live Bitcoin news and market headlines')

def test_classify_lviv_as_city_via_aliases():
    assert classify_topic('Львів') == 'city'
    plan = build_search_plan('Kharkov', from_dt=datetime.now(tz=timezone.utc)-timedelta(days=7), to_dt=datetime.now(tz=timezone.utc), first_run=True)
    assert plan.topic_kind == 'city'
    assert any('local government' in q.lower() or 'city latest developments' in q.lower() for q in plan.query_variants)


def test_reject_stock_analysis_for_ambiguous_symbol():
    plan = build_search_plan('NAVI', from_dt=datetime.now(tz=timezone.utc)-timedelta(days=7), to_dt=datetime.now(tz=timezone.utc), first_run=True)
    assert not is_candidate_article(
        plan,
        url='https://news.stocktradersdaily.com/news_release/90/Understanding+Momentum+Shifts+in+(NAVI)_04222026.html',
        title='Understanding Momentum Shifts in (NAVI)',
        description='Stock analysis and momentum shifts in NAVI shares',
    )
