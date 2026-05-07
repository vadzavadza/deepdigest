# Test report v6

## Static checks

- Python source syntax checked via direct `compile(source, filename, "exec")` for changed Python files: PASS.
- Deterministic candidate checks for v6 core logic: PASS.
- Zip integrity: PASS after archive creation.

## Deterministic checks covered

- `NAVI TEAM` normalizes to `navi` so generic suffix `TEAM` does not become a required exact phrase.
- `Rome city` normalizes to `rome` when the remaining term is a known city alias.
- A direct NAVI/CS2 article no longer fails only because it lacks the exact phrase `NAVI TEAM`.
- A strong OpenRouter search annotation without verified date can become `weak_but_usable` instead of being dropped.
- A verified article just outside the 7-day soft window can still be accepted if it is inside the 30-day hard window.
- A very old article is still rejected as `old`.

## Not run here

- Live OpenRouter calls.
- Live Telegram publishing.
- Full Docker integration with your `.env`.

Those require your real keys and local Docker environment.
