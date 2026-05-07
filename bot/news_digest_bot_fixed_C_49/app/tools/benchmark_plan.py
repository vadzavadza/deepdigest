from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.search_v2.strategy import build_search_plan


def load_topics(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run the universal topic classifier/query planner without calling OpenRouter.")
    parser.add_argument("--input", default="eval_fixtures/benchmark_topics.jsonl")
    parser.add_argument("--out", default="debug_runs/benchmark_plan_report.md")
    parser.add_argument("--json-out", default="debug_runs/benchmark_plan_report.json")
    args = parser.parse_args()

    now = datetime.now(tz=timezone.utc)
    rows = load_topics(Path(args.input))
    report_rows = []
    lines = ["# Benchmark query-plan report", ""]
    mismatches = 0
    for row in rows:
        plan = build_search_plan(row["topic"], from_dt=now - timedelta(days=7), to_dt=now, first_run=True)
        ok = plan.topic_kind == row.get("expected_kind")
        if not ok:
            mismatches += 1
        report_rows.append({
            **row,
            "detected_kind": plan.topic_kind,
            "normalized_query": plan.normalized_query,
            "query_variants": plan.query_variants,
            "required_terms": sorted(plan.required_terms),
            "soft_terms": sorted(plan.soft_terms),
            "semantic_hints": sorted(plan.semantic_hints),
            "matches_expected_kind": ok,
        })
        lines.extend([
            f"## {row['topic']}  `expected={row.get('expected_kind')}`  `detected={plan.topic_kind}`  `ok={ok}`",
            "",
            f"- normalized: `{plan.normalized_query}`",
            f"- acceptable: {row.get('acceptable', '-')}",
            f"- bad: {row.get('bad', '-')}",
            "- query variants:",
        ])
        for q in plan.query_variants:
            lines.append(f"  - `{q}`")
        lines.append("")
    lines.insert(2, f"Classifier mismatches: **{mismatches}/{len(rows)}**\n")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    Path(args.json_out).write_text(json.dumps(report_rows, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out}; mismatches={mismatches}/{len(rows)}")


if __name__ == "__main__":
    main()
