from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from meeting_workflow_state import parse_frontmatter, relpath, repo_root_from, unknownish
from render_meeting_repo import validate_repo


DASHBOARD_TARGETS = (
    "00_Dashboard/Meeting_HOME.md",
    "00_Dashboard/Action_Queue.md",
    "00_Dashboard/Decision_Register.md",
)
PROHIBITED_API_PATTERNS = (
    re.compile(r"\bOPENAI_API_KEY\b"),
    re.compile(r"\bapi_key\b", re.IGNORECASE),
    re.compile(r"\bchat\.completions\b"),
    re.compile(r"\bresponses\.create\b"),
    re.compile(r"^\s*(from\s+openai\s+import|import\s+openai)\b", re.MULTILINE),
    re.compile(r"\bopenai\.OpenAI\b"),
)


def quality_gate(root: Path) -> List[str]:
    root = root.resolve()
    errors: List[str] = []
    errors.extend(validate_repo(root))
    errors.extend(_check_dashboard_targets(root))
    errors.extend(_check_child_parent_meeting(root))
    errors.extend(_check_actions_review_required(root))
    errors.extend(_check_validated_evidence(root))
    errors.extend(_check_workflow_state_artifacts(root))
    errors.extend(_check_no_api_automation(root))
    return errors


def _minutes_data_files(root: Path) -> Iterable[Path]:
    base = root / "25_Meetings"
    if not base.exists():
        return []
    return sorted(base.glob("*/_data/gpt_minutes.json"))


def _check_dashboard_targets(root: Path) -> List[str]:
    if not list(_minutes_data_files(root)):
        return []
    return [f"missing dashboard target: {target}" for target in DASHBOARD_TARGETS if not (root / target).exists()]


def _check_child_parent_meeting(root: Path) -> List[str]:
    errors: List[str] = []
    for data_path in _minutes_data_files(root):
        meeting_id = data_path.parents[1].name
        meeting_dir = root / "25_Meetings" / meeting_id
        data = json.loads(data_path.read_text(encoding="utf-8"))
        for group, folder in (("decisions", "decisions"), ("actions", "actions"), ("issues", "issues")):
            for item in data.get(group, []):
                item_id = str(item.get("id", ""))
                path = meeting_dir / folder / f"{item_id}.md"
                if not path.exists():
                    continue
                frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
                if frontmatter.get("parent_meeting") != meeting_id:
                    errors.append(f"{relpath(path, root)}: parent_meeting must be {meeting_id}")
    return errors


def _check_actions_review_required(root: Path) -> List[str]:
    errors: List[str] = []
    for data_path in _minutes_data_files(root):
        data = json.loads(data_path.read_text(encoding="utf-8"))
        for item in data.get("actions", []):
            if (unknownish(item.get("owner")) or unknownish(item.get("due"))) and not item.get("review_required"):
                errors.append(f"{relpath(data_path, root)}: {item.get('id', '<action>')} missing owner/due requires review_required")
    return errors


def _check_validated_evidence(root: Path) -> List[str]:
    errors: List[str] = []
    for path in sorted((root / "25_Meetings").glob("**/*.md")):
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
        status = str(frontmatter.get("status", "")).strip().lower()
        if status in {"validated", "stable", "approved"} and not frontmatter.get("evidence_ref"):
            errors.append(f"{relpath(path, root)}: {status} note must include evidence_ref")
    return errors


def _check_workflow_state_artifacts(root: Path) -> List[str]:
    errors: List[str] = []
    workflow_dir = root / ".workflow"
    if not workflow_dir.exists():
        return errors
    for path in sorted(workflow_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"{relpath(path, root)}: invalid workflow state JSON")
            continue
        meeting_id = str(data.get("meeting_id", "")).strip()
        status = str(data.get("workflow_step") or data.get("status") or "").strip().upper()
        if meeting_id and status in {"GPT_INPUT_READY", "GPT_OUTPUT_PENDING", "GPT_OUTPUT_SELECTED"}:
            gpt_input = root / "40_Work" / f"{meeting_id}_gpt_input.md"
            if not gpt_input.exists():
                errors.append(f"{relpath(path, root)}: missing GPT input file {relpath(gpt_input, root)}")
        if meeting_id and status in {"IMPORT_PREVIEWED", "IMPORT_APPLIED"}:
            output = data.get("gpt_output_file")
            if not output or not Path(str(output)).exists():
                errors.append(f"{relpath(path, root)}: import state references missing gpt_output_file")
    return errors


def _check_no_api_automation(root: Path) -> List[str]:
    errors: List[str] = []
    if (root / "openai_client.py").exists() or (root / "scripts" / "openai_client.py").exists():
        errors.append("openai_client.py must not exist in the manual no-API workflow")
    for path in sorted((root / "scripts").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for pattern in PROHIBITED_API_PATTERNS:
            if pattern.search(text):
                errors.append(f"{relpath(path, root)}: prohibited OpenAI API automation pattern {pattern.pattern}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the scoped 09_Meeting manual GPT quality gate.")
    parser.add_argument("--root", type=Path, default=repo_root_from(), help="09_Meeting repository root.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    errors = quality_gate(args.root)
    if errors:
        print("QUALITY GATE FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("QUALITY GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
