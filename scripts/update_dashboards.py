from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from meeting_workflow_state import markdown_table, normalize_minutes, relpath, replace_blocks_in_file, repo_root_from


def update_dashboards(root: Path, apply: bool = False) -> List[str]:
    root = root.resolve()
    minutes = _load_all_minutes(root)
    dashboard_dir = root / "30_Dashboards"
    actions: List[str] = []
    actions.append(
        replace_blocks_in_file(
            dashboard_dir / "meeting_dashboard.md",
            "# Meeting Dashboard\n\n<!-- AUTO-GENERATED: DASHBOARD START -->\nNo meetings.\n<!-- AUTO-GENERATED: DASHBOARD END -->\n",
            {"DASHBOARD": _meeting_dashboard(minutes)},
            apply=apply,
        )
    )
    actions.append(
        replace_blocks_in_file(
            dashboard_dir / "review_required.md",
            "# Review Required\n\n<!-- AUTO-GENERATED: DASHBOARD START -->\nNo review items.\n<!-- AUTO-GENERATED: DASHBOARD END -->\n",
            {"DASHBOARD": _review_dashboard(minutes)},
            apply=apply,
        )
    )
    return actions


def _load_all_minutes(root: Path) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for path in sorted((root / "25_Meetings").glob("*/_data/gpt_minutes.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        result.append(normalize_minutes(data, path.parents[1].name))
    return sorted(result, key=lambda item: str(item.get("meeting_id", "")))


def _meeting_dashboard(minutes: List[Dict[str, Any]]) -> str:
    rows = [
        [
            item["meeting_id"],
            item.get("title", ""),
            item.get("meeting_date", ""),
            len(item.get("decisions", [])),
            len(item.get("actions", [])),
            len(item.get("issues", [])),
            "yes" if item.get("review", {}).get("review_required") else "no",
        ]
        for item in minutes
    ]
    return markdown_table(["Meeting", "Title", "Date", "Decisions", "Actions", "Issues", "Review"], rows)


def _review_dashboard(minutes: List[Dict[str, Any]]) -> str:
    rows: List[List[str]] = []
    for meeting in minutes:
        meeting_id = meeting["meeting_id"]
        for kind, group, field in (
            ("decision", "decisions", "title"),
            ("action", "actions", "task"),
            ("issue", "issues", "issue"),
        ):
            for item in meeting.get(group, []):
                if item.get("review_required"):
                    rows.append([meeting_id, kind, item["id"], item.get(field, "")])
    return markdown_table(["Meeting", "Kind", "ID", "Item"], rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update manual GPT meeting dashboards.")
    parser.add_argument("--root", type=Path, default=repo_root_from(), help="09_Meeting repository root.")
    parser.add_argument("--apply", action="store_true", help="Write files. Defaults to dry run.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    actions = update_dashboards(args.root, apply=args.apply)
    print("APPLY" if args.apply else "DRY RUN")
    for action in actions:
        print(f"- {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
