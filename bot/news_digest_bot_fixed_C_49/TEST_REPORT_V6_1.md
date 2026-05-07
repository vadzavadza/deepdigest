# Test report v6.1

- `py_compile` for changed runtime files: PASS
- Added deterministic tests: `tests/test_quality_engine_v61.py`
- Full pytest was not executed in this sandbox because the available runtime pytest environment was not responsive here.

Recommended local command:

```bash
pytest -q tests/test_quality_engine_v6.py tests/test_quality_engine_v61.py tests/test_ranking.py tests/test_search_v2.py tests/test_quality_filters.py
```
