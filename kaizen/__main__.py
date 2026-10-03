"""Command line: run a gate, show a run's status, or act as a Claude Code hook.

    python -m kaizen schema <stage>
    python -m kaizen fetch <url> --run <run_dir> --source-type <type> --relation <relation>
    python -m kaizen gate <stage> <run_dir>
    python -m kaizen status <run_dir>
    python -m kaizen hook            (reads the hook event JSON on stdin)

Output is ASCII only so it survives any console code page.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from kaizen.gate import STAGES, run_gate, upstream_passed

REPO_ROOT = Path(__file__).resolve().parent.parent


def _print_report(stage: str, rpt: dict) -> None:
    status = "PASS" if rpt["passed"] else "FAIL"
    print(f"[{status}] {stage}")
    for k, v in rpt.get("metrics", {}).items():
        print(f"    {k}: {v}")
    for v in rpt.get("violations", []):
        print(f"    - {v['code']}: {v['detail']}")
    for v in rpt.get("warnings", []):
        print(f"    ~ warning {v['code']}: {v['detail']}")


def cmd_gate(stage: str, run_dir: str) -> int:
    if stage not in STAGES:
        print(f"unknown stage {stage!r}; stages: {', '.join(STAGES)}")
        return 2
    report = run_gate(stage, Path(run_dir).resolve(), REPO_ROOT)
    _print_report(stage, report.to_dict())
    return 0 if report.passed else 1


def cmd_status(run_dir: str) -> int:
    rd = Path(run_dir).resolve()
    for stage in STAGES:
        rpt = rd / f"{stage}.gate.json"
        if rpt.exists():
            _print_report(stage, json.loads(rpt.read_text(encoding="utf-8")))
        elif (rd / f"{stage}.json").exists():
            print(f"[----] {stage}: artifact written, gate not run")
        else:
            print(f"[    ] {stage}: not started")
    return 0


def _stage_for(path: Path) -> str | None:
    """A stage artifact is runs/<run>/<stage>.json."""
    if path.suffix != ".json" or path.parent.parent.name != "runs":
        return None
    return path.stem if path.stem in STAGES else None


def cmd_hook() -> int:
    """
    PreToolUse  (Write|Edit on a stage artifact): block if the upstream stage has not passed.
    PostToolUse (Write|Edit on a stage artifact): run the gate; exit 2 sends the violations back
    to the agent so it fixes the artifact before moving on.
    """
    event = json.load(sys.stdin)
    raw = (event.get("tool_input") or {}).get("file_path") or ""
    if not raw:
        return 0
    m = re.match(r"^/([a-zA-Z])/(.*)$", raw)
    if m and sys.platform == "win32":  # MSYS-style path from a POSIX shell on Windows
        raw = f"{m.group(1)}:/{m.group(2)}"
    path = Path(raw).resolve()
    if any(p.name == "corpus" and p.parent.parent.name == "runs" for p in path.parents):
        if event.get("hook_event_name") == "PreToolUse":
            print(
                "kaizen: blocked writing into the research corpus: pages are saved by "
                "`python -m kaizen fetch`, never written by an agent",
                file=sys.stderr,
            )
            return 2
        return 0
    if path.parent.parent.name == "runs" and (path.name.endswith(".gate.json") or path.name == "evidence.scored.json"):
        if event.get("hook_event_name") == "PreToolUse":
            print(f"kaizen: blocked writing {path.name}: gate output is written by the gate, not by an agent", file=sys.stderr)
            return 2
        return 0
    stage = _stage_for(path)
    if stage is None:
        return 0
    run_dir = path.parent

    if event.get("hook_event_name") == "PreToolUse":
        ok, why = upstream_passed(run_dir, stage)
        if not ok:
            print(f"kaizen: blocked writing {stage}: {why}", file=sys.stderr)
            return 2
        return 0

    report = run_gate(stage, run_dir, REPO_ROOT)
    if report.passed:
        notes = "".join(f"\n  ~ warning {w.code}: {w.detail}" for w in report.warnings)
        print(f"kaizen: {stage} gate passed{notes}", file=sys.stderr)
        return 0
    lines = [f"kaizen: {stage} gate FAILED. Fix the artifact and write it again:"]
    lines += [f"  - {v.code}: {v.detail}" for v in report.violations]
    print("\n".join(lines), file=sys.stderr)
    return 2


def cmd_schema(stage: str) -> int:
    """Print the JSON schema an agent must write for a stage: one source of truth for the shape."""
    from kaizen.gate import EvidenceFile, ResearchPlan, StageArtifact
    from kaizen.message_spine_contract import SECTION_INTENT as SPINE_INTENT
    from kaizen.message_spine_contract import MessageSpineStructuredPayload
    from kaizen.strategy_brief_contract import SECTION_INTENT as BRIEF_INTENT
    from kaizen.strategy_brief_contract import TRANSFORMATION_BOUNDARIES, StrategyBriefStructuredPayload

    if stage == "research":
        from kaizen.fetch import AUTHOR_RELATIONS, SOURCE_TYPES

        out = {
            "file": "research.json",
            "schema": ResearchPlan.model_json_schema(),
            "fetch_source_types": list(SOURCE_TYPES),
            "fetch_author_relations": list(AUTHOR_RELATIONS),
        }
    elif stage == "evidence":
        out = {"file": "evidence.json", "schema": EvidenceFile.model_json_schema()}
    elif stage in ("strategy_brief", "message_spine"):
        model = StrategyBriefStructuredPayload if stage == "strategy_brief" else MessageSpineStructuredPayload
        intent = BRIEF_INTENT if stage == "strategy_brief" else SPINE_INTENT
        out = {
            "file": f"{stage}.json",
            "envelope": StageArtifact.model_json_schema(),
            "payload_schema": model.model_json_schema(),
            "section_intent": {str(k): v for k, v in intent.items()},
        }
        if stage == "strategy_brief":
            out["transformation_boundaries"] = TRANSFORMATION_BOUNDARIES
    else:
        print(f"unknown stage {stage!r}; stages: {', '.join(STAGES)}")
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=True))
    return 0


def cmd_fetch(argv: list[str]) -> int:
    import argparse

    from kaizen.fetch import AUTHOR_RELATIONS, SOURCE_TYPES, FetchError, fetch_page, save_to_corpus

    ap = argparse.ArgumentParser(prog="python -m kaizen fetch")
    ap.add_argument("url")
    ap.add_argument("--run", required=True, help="run directory, e.g. runs/my-run")
    ap.add_argument("--source-type", required=True, choices=SOURCE_TYPES)
    ap.add_argument("--relation", required=True, choices=AUTHOR_RELATIONS)
    args = ap.parse_args(argv)
    try:
        page = fetch_page(args.url)
        path = save_to_corpus(
            page,
            Path(args.run).resolve() / "corpus",
            source_type=args.source_type,
            author_relation=args.relation,
        )
    except FetchError as e:
        print(f"fetch refused: {e}")
        return 1
    print(f"saved {path.name}")
    print(f"    title: {page.title.encode('ascii', 'replace').decode()}")
    print(f"    published: {page.published or 'none found'}")
    print(f"    chars: {len(page.text)}")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["fetch"]:
        return cmd_fetch(argv[1:])
    if len(argv) >= 2 and argv[0] == "schema":
        return cmd_schema(argv[1])
    if len(argv) >= 3 and argv[0] == "gate":
        return cmd_gate(argv[1], argv[2])
    if len(argv) >= 2 and argv[0] == "status":
        return cmd_status(argv[1])
    if argv[:1] == ["hook"]:
        return cmd_hook()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
