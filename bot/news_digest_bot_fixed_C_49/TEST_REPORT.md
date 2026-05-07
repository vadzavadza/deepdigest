# TEST_REPORT

## What I could test here

- `py_compile` for all `app/**/*.py` and `tests/**/*.py`: PASS
- Deterministic smoke checks run manually: PASS
  - generic topic classification: `country`, `city`, `geo_region`, `team_org`, `person`, `business`, `crypto`
  - news hub / section pages are rejected
  - evergreen guide content is rejected for news digest topics
  - indirect country relevance is rejected locally
  - budget settings are present in `.env.example` and `app/shared/settings.py`

## What I could not fully test here

- Live OpenRouter calls: not run, because this environment does not have your API key and real billing setup.
- Live Telegram publish: not run, because this environment does not have your bot token/channel.
- Full `pytest -q`: previously attempted in this environment and hung during pytest startup/import, so I validated syntax and deterministic checks directly instead.

## Recommended first local commands

```bash
pytest -q tests/test_search_v2.py tests/test_disambiguation_diversity.py tests/test_quality_filters.py tests/test_quality_engine_v5.py
pytest -q
```

If anything fails, send the full traceback and the command you used.
