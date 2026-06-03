from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from meeting_workflow_state import markdown_table, normalize_minutes, relpath, replace_blocks_in_file, repo_root_from


def update_dashboards(root: Path, apply: bool = False) -> List[str]:
    root = root.resolve()
    minutes = _load_all_minutes(root)
    dashboard_dir = root / "00_Dashboard"
    actions: List[str] = []
    actions.append(
        replace_blocks_in_file(
            dashboard_dir / "Meeting_HOME.md",
            "# Meeting HOME\n\n<!-- AUTO-GENERATED: DASHBOARD START -->\nNo meetings.\n<!-- AUTO-GENERATED: DASHBOARD END -->\n",
            {"DASHBOARD": _meeting_home(minutes)},
            apply=apply,
        )
    )
    actions.append(
        replace_blocks_in_file(
            dashboard_dir / "Action_Queue.md",
            "# Action Queue\n\n<!-- AUTO-GENERATED: DASHBOARD START -->\nNo actions.\n<!-- AUTO-GENERATED: DASHBOARD END -->\n",
            {"DASHBOARD": _action_queue(minutes)},
            apply=apply,
        )
    )
    actions.append(
        replace_blocks_in_file(
            dashboard_dir / "Decision_Register.md",
            "# Decision Register\n\n<!-- AUTO-GENERATED: DASHBOARD START -->\nNo decisions.\n<!-- AUTO-GENERATED: DASHBOARD END -->\n",
            {"DASHBOARD": _decision_register(minutes)},
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


def _meeting_home(minutes: List[Dict[str, Any]]) -> str:
    rows = [
        [
            item["meeting_id"],
            item.get("title", ""),
            item.get("meeting_date", ""),
            len(item.get("decisions", [])),
            len(item.get("actions", [])),
            len(item.get("issues", [])),
            "yes" if item.get("review", {}).get("review_required") else "no",
            _meeting_status(item),
        ]
        for item in minutes
    ]
    return markdown_table(["Meeting", "Title", "Date", "Decisions", "Actions", "Issues", "Review", "Status"], rows)


def _action_queue(minutes: List[Dict[str, Any]]) -> str:
    rows: List[List[str]] = []
    for meeting in minutes:
        meeting_id = meeting["meeting_id"]
        for item in meeting.get("actions", []):
            rows.append(
                [
                    meeting_id,
                    item["id"],
                    item.get("task", ""),
                    item.get("owner", "Unknown"),
                    item.get("due", "Unknown"),
                    "yes" if item.get("review_required") else "no",
                    _item_status(item),
                ]
            )
    return markdown_table(["Meeting", "Action", "Task", "Owner", "Due", "Review", "Status"], rows)


def _decision_register(minutes: List[Dict[str, Any]]) -> str:
    rows: List[List[str]] = []
    for meeting in minutes:
        meeting_id = meeting["meeting_id"]
        for item in meeting.get("decisions", []):
            rows.append(
                [
                    meeting_id,
                    item["id"],
                    item.get("title", ""),
                    item.get("decider", "Unknown"),
                    item.get("owner", "Unknown"),
                    item.get("due", "Unknown"),
                    "yes" if item.get("review_required") else "no",
                    _item_status(item),
                ]
            )
    return markdown_table(["Meeting", "Decision", "Title", "Decider", "Owner", "Due", "Review", "Status"], rows)


def _meeting_status(item: Dict[str, Any]) -> str:
    return "review" if item.get("review", {}).get("review_required") else "draft"


def _item_status(item: Dict[str, Any]) -> str:
    return "review" if item.get("review_required") else "draft"


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
