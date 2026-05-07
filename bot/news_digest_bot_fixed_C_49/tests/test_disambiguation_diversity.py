from datetime import datetime, timezone

from app.domain.policies.ranking import select_diverse_stories
from app.schemas.articles import NormalizedArticle
from app.schemas.sources import StoryCandidate
from app.search_v2.article_filter import is_candidate_article
from app.search_v2.strategy import build_search_plan, classify_topic


def test_classify_team_spirit_as_team_org() -> None:
    assert classify_topic('Team Spirit') == 'team_org'
    plan = build_search_plan('Team Spirit', from_dt=datetime.now(tz=timezone.utc), to_dt=datetime.now(tz=timezone.utc), first_run=True)
    assert any('organization' in q.lower() or 'esports' in q.lower() for q in plan.query_variants)


def test_reject_team_spirit_generic_phrase_story() -> None:
    plan = build_search_plan('Team Spirit', from_dt=datetime.now(tz=timezone.utc), to_dt=datetime.now(tz=timezone.utc), first_run=True)
    assert not is_candidate_article(
        plan,
        url='https://www.flashscore.fi/uutinen/team-spirit-key-to-colombia-run/123',
        title="Team spirit key to Colombia's remarkable Copa América run",
        description='Coach says team spirit was key to the run',
    )


def test_select_diverse_stories_penalizes_same_domain() -> None:
    now = datetime.now(tz=timezone.utc)
    strong_a = NormalizedArticle(
        provider='a', url='https://bo3.gg/story-a', title='Dota 2 roster move', description='Roster move',
        source_name='bo3.gg', source_language='en', published_at=now, normalized_title='dota 2 roster move', canonical_key='dota 2 roster move',
    )
    strong_b = NormalizedArticle(
        provider='b', url='https://bo3.gg/story-b', title='Dota 2 legal dispute', description='Legal dispute',
        source_name='bo3.gg', source_language='en', published_at=now, normalized_title='dota 2 legal dispute', canonical_key='dota 2 legal dispute',
    )
    alt = NormalizedArticle(
        provider='c', url='https://hltv.org/story-c', title='Dota 2 tournament update', description='Tournament update',
        source_name='HLTV.org', source_language='en', published_at=now, normalized_title='dota 2 tournament update', canonical_key='dota 2 tournament update',
    )
    stories = [
        StoryCandidate(story_hash='a', canonical_title='A', articles=[strong_a]),
        StoryCandidate(story_hash='b', canonical_title='B', articles=[strong_b]),
        StoryCandidate(story_hash='c', canonical_title='C', articles=[alt]),
    ]
    selected = select_diverse_stories(stories, 2)
    hosts = {str(storiesel.articles[0].url).split('/')[2] for storiesel in selected}
    assert 'hltv.org' in hosts
