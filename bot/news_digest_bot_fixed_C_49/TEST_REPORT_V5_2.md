# Test report v5.2

Checked in this environment:

- `py_compile` for modified Python files: PASS
- Manual deterministic filter checks: PASS
  - `python` classified as `technology`
  - `BLAST CS` classified as `esports`
  - `Microsoft News | Windows Central` rejected as `topic_news_hub_page`
  - Python snake/zoo result rejected via negative context

Not fully run here:

- Full `pytest`, because this container hangs while importing some installed runtime dependencies. The files are syntax-checked, and the new deterministic tests are included for your local environment.

Recommended local command:

```bash
pytest -q tests/test_quality_engine_v52.py tests/test_freshness_guard_v51.py tests/test_search_v2.py tests/test_deduplication.py tests/test_quality_filters.py
```
