from __future__ import annotations

import argparse
import glob
import json
from collections import Counter, defaultdict
from app.search_v2.source_quality import source_quality_weight, source_authority_tier
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_counter(counter: dict[str, int], *, limit: int = 10) -> str:
    if not counter:
        return "-"
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return ", ".join(f"{k}: {v}" for k, v in items)


def analyze_run(data: dict[str, Any]) -> dict[str, Any]:
    decisions = data.get("candidate_decisions") or []
    raw_candidates = data.get("raw_candidates") or []
    final_items = data.get("final_items") or []
    status_counts = Counter(str(d.get("status") or "unknown") for d in decisions)
    reason_counts = Counter(str(d.get("reason") or "unknown") for d in decisions)
    domains = Counter(str(d.get("domain") or "unknown") for d in decisions)
    final_domains = Counter(str((item.get("url") or "").split("/")[2].replace("www.", "") if item.get("url") and "/" in item.get("url") else item.get("source_name") or "unknown") for item in final_items)
    weak = status_counts.get("weak_but_usable", 0)
    accepted = status_counts.get("accepted", 0)
    topic_kind = str(data.get("topic_kind") or "")
    final_source_weights = [source_quality_weight(item.get("source_name") or item.get("url") or "", topic_kind) for item in final_items]
    weak_final_sources = sum(1 for weight in final_source_weights if weight < 0)
    strong_final_sources = sum(1 for weight in final_source_weights if weight >= 16)
    hard_rejects = sum(v for k, v in status_counts.items() if k not in {"accepted", "weak_but_usable"})
    return {
        "run_id": data.get("run_id"),
        "topic": data.get("topic"),
        "normalized_topic": data.get("normalized_topic"),
        "topic_kind": data.get("topic_kind"),
        "status": data.get("status"),
        "raw_count": len(raw_candidates),
        "decision_count": len(decisions),
        "accepted_count": accepted,
        "weak_count": weak,
        "hard_rejects": hard_rejects,
        "final_count": len(final_items),
        "status_counts": dict(status_counts),
        "reason_counts": dict(reason_counts),
        "candidate_domains": dict(domains),
        "final_domains": dict(final_domains),
        "final_source_weights": final_source_weights,
        "weak_final_sources": weak_final_sources,
        "strong_final_sources": strong_final_sources,
        "query_variants": data.get("query_variants") or [],
        "pass_stats": data.get("pass_stats") or [],
    }


def grade_run(summary: dict[str, Any]) -> tuple[str, list[str]]:
    notes: list[str] = []
    final_count = int(summary["final_count"])
    raw_count = int(summary["raw_count"])
    accepted_count = int(summary["accepted_count"])
    weak_count = int(summary["weak_count"])
    reasons = summary.get("reason_counts") or {}
    if raw_count == 0:
        notes.append("provider_returned_zero")
    if raw_count > 0 and final_count == 0:
        notes.append("filter_or_selection_zeroed_results")
    if final_count > 0 and accepted_count == 0 and weak_count > 0:
        notes.append("only_weak_freshness_selected")
    if reasons.get("topic_news_hub_page") or reasons.get("news_hub_page"):
        notes.append("hub_pages_present_in_candidates")
    if reasons.get("review_or_buying_guide"):
        notes.append("review_or_buying_guide_candidates_present")
    if reasons.get("outside_hard_freshness_window"):
        notes.append("old_candidates_present")
    weak_final_sources = int(summary.get("weak_final_sources") or 0)
    strong_final_sources = int(summary.get("strong_final_sources") or 0)
    if weak_final_sources:
        notes.append("weak_sources_in_final")
    if final_count >= 3 and accepted_count >= 2 and weak_final_sources == 0 and strong_final_sources >= 1:
        grade = "good"
    elif final_count >= 1 and (accepted_count >= 1 or weak_count >= 1) and weak_final_sources <= 1:
        grade = "usable"
    elif raw_count > 0:
        grade = "retrieval_ok_filter_failed"
    else:
        grade = "retrieval_failed"
    return grade, notes


def render_markdown(summaries: list[dict[str, Any]]) -> str:
    lines = ["# Search replay report", ""]
    aggregate_grades = Counter()
    aggregate_reasons = Counter()
    by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    for summary in summaries:
        grade, notes = grade_run(summary)
        aggregate_grades[grade] += 1
        by_kind[str(summary.get("topic_kind") or "unknown")][grade] += 1
        aggregate_reasons.update(summary.get("reason_counts") or {})
        lines.extend([
            f"## {summary.get('topic')}  `kind={summary.get('topic_kind')}`  `grade={grade}`",
            "",
            f"- run: `{summary.get('run_id')}`",
            f"- raw candidates: **{summary['raw_count']}**",
            f"- decisions: **{summary['decision_count']}**",
            f"- accepted: **{summary['accepted_count']}**, weak: **{summary['weak_count']}**, final selected: **{summary['final_count']}**",
            f"- statuses: {_fmt_counter(summary.get('status_counts') or {})}",
            f"- reasons: {_fmt_counter(summary.get('reason_counts') or {})}",
            f"- final domains: {_fmt_counter(summary.get('final_domains') or {})}",
            f"- notes: {', '.join(notes) if notes else '-'}",
            "",
        ])
    lines.extend([
        "# Aggregate",
        "",
        f"- runs: **{len(summaries)}**",
        f"- grades: {_fmt_counter(dict(aggregate_grades))}",
        f"- top rejection reasons: {_fmt_counter(dict(aggregate_reasons), limit=15)}",
        "",
        "## By topic kind",
        "",
    ])
    for kind, counter in sorted(by_kind.items()):
        lines.append(f"- `{kind}`: {_fmt_counter(dict(counter))}")
    lines.append("")
    return "\n".join(lines)


def expand_inputs(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        matches = [Path(p) for p in glob.glob(item)]
        if matches:
            paths.extend(matches)
        else:
            paths.append(Path(item))
    unique = []
    seen = set()
    for path in paths:
        if path in seen or not path.exists() or path.suffix.lower() != ".json":
            continue
        unique.append(path)
        seen.add(path)
    return sorted(unique)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze saved v6.3 search run JSON files without spending OpenRouter credits.")
    parser.add_argument("inputs", nargs="+", help="Run JSON files or globs, e.g. debug_runs/*.json")
    parser.add_argument("--out", default="debug_runs/replay_report.md", help="Markdown output path")
    parser.add_argument("--json-out", default=None, help="Optional JSON summary output path")
    args = parser.parse_args()

    paths = expand_inputs(args.inputs)
    summaries = [analyze_run(_load_json(path)) for path in paths]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(summaries), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(summaries, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Analyzed {len(summaries)} run(s). Report: {out}")


if __name__ == "__main__":
    main()
