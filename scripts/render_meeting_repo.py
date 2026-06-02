from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from import_gpt_minutes import render_minutes_artifacts
from meeting_workflow_state import (
    generated_block_errors,
    is_relative_to,
    normalize_minutes,
    normalize_relpath,
    parse_frontmatter,
    relpath,
    repo_root_from,
    review_required_for_item,
    validate_derived_id,
    validate_meeting_id,
)


RAW_EXTENSIONS = {
    ".aac",
    ".docx",
    ".flac",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".rtf",
    ".srt",
    ".vtt",
    ".wav",
    ".webm",
}


def render_repo(root: Path, meeting_id: str = "", apply: bool = False) -> List[str]:
    root = root.resolve()
    actions: List[str] = []
    for data_path in _minutes_data_files(root, meeting_id):
        minutes = json.loads(data_path.read_text(encoding="utf-8"))
        normalized = normalize_minutes(minutes, data_path.parents[1].name)
        actions.extend(render_minutes_artifacts(root, normalized["meeting_id"], normalized, apply=apply))
    return actions


def validate_repo(root: Path) -> List[str]:
    root = root.resolve()
    errors: List[str] = []
    errors.extend(_check_raw_locations(root))
    errors.extend(_check_source_to_main_links(root))
    errors.extend(_check_main_item_links(root))
    errors.extend(_check_review_required(root))
    errors.extend(_check_id_policy(root))
    errors.extend(_check_generated_blocks(root))
    return errors


def _minutes_data_files(root: Path, meeting_id: str = "") -> Iterable[Path]:
    base = root / "25_Meetings"
    if meeting_id:
        path = base / meeting_id / "_data" / "gpt_minutes.json"
        return [path] if path.exists() else []
    if not base.exists():
        return []
    return sorted(base.glob("*/_data/gpt_minutes.json"))


def _check_raw_locations(root: Path) -> List[str]:
    errors: List[str] = []
    archive = root / "20_Sources" / "00_Originals"
    skip_dirs = {".git", ".workflow", "__pycache__", ".pytest_cache"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix.lower() not in RAW_EXTENSIONS:
            continue
        if path.stat().st_size == 0:
            continue
        if not is_relative_to(path, archive):
            errors.append(f"raw file outside 20_Sources/00_Originals: {relpath(path, root)}")
    return errors


def _check_source_to_main_links(root: Path) -> List[str]:
    errors: List[str] = []
    source_dir = root / "20_Sources"
    if not source_dir.exists():
        return errors
    for path in sorted(source_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        if frontmatter.get("type") != "source":
            continue
        main_rel = normalize_relpath(str(frontmatter.get("main_note", "")))
        if not main_rel:
            errors.append(f"{relpath(path, root)}: missing main_note")
            continue
        main_path = root / main_rel
        if not main_path.exists():
            errors.append(f"{relpath(path, root)}: main_note does not exist: {main_rel}")
            continue
        main_fm = parse_frontmatter(main_path.read_text(encoding="utf-8"))
        expected_source = relpath(path, root)
        actual_source = normalize_relpath(str(main_fm.get("source_note", "")))
        if actual_source and actual_source != expected_source:
            errors.append(
                f"{relpath(main_path, root)}: source_note {actual_source} does not match {expected_source}"
            )
    return errors


def _check_main_item_links(root: Path) -> List[str]:
    errors: List[str] = []
    for data_path in _minutes_data_files(root):
        minutes = normalize_minutes(json.loads(data_path.read_text(encoding="utf-8")), data_path.parents[1].name)
        meeting_id = minutes["meeting_id"]
        meeting_dir = root / "25_Meetings" / meeting_id
        main_path = meeting_dir / f"{meeting_id}.md"
        if not main_path.exists():
            errors.append(f"{relpath(data_path, root)}: missing main note {meeting_id}.md")
            continue
        main_text = main_path.read_text(encoding="utf-8")
        for group, folder in (("decisions", "decisions"), ("actions", "actions"), ("issues", "issues")):
            for item in minutes[group]:
                child_rel = f"{folder}/{item['id']}.md"
                child_path = meeting_dir / child_rel
                if not child_path.exists():
                    errors.append(f"{relpath(main_path, root)}: missing linked {group[:-1]} note {child_rel}")
                if child_rel not in main_text:
                    errors.append(f"{relpath(main_path, root)}: missing link to {child_rel}")
                if child_path.exists() and f"../{meeting_id}.md" not in child_path.read_text(encoding="utf-8"):
                    errors.append(f"{relpath(child_path, root)}: missing backlink to main note")
    return errors


def _check_review_required(root: Path) -> List[str]:
    errors: List[str] = []
    for data_path in _minutes_data_files(root):
        minutes = json.loads(data_path.read_text(encoding="utf-8"))
        meeting_id = data_path.parents[1].name
        for kind, group in (("decision", "decisions"), ("action", "actions"), ("issue", "issues")):
            for index, item in enumerate(minutes.get(group, []), start=1):
                if review_required_for_item(kind, item) and not item.get("review_required"):
                    item_id = item.get("id", f"{kind}-{index}")
                    errors.append(
                        f"{relpath(data_path, root)}: {item_id} must set review_required for missing owner/decider/due"
                    )
        main_path = root / "25_Meetings" / meeting_id / f"{meeting_id}.md"
        if main_path.exists():
            fm = parse_frontmatter(main_path.read_text(encoding="utf-8"))
            if fm.get("speaker_reliable") is not False:
                errors.append(f"{relpath(main_path, root)}: speaker_reliable must remain false")
            if fm.get("role_reliable") is not False:
                errors.append(f"{relpath(main_path, root)}: role_reliable must remain false")
    return errors


def _check_id_policy(root: Path) -> List[str]:
    errors: List[str] = []
    for path in sorted((root / "20_Sources").glob("*.md")):
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
        meeting_id = str(frontmatter.get("meeting_id", ""))
        if meeting_id and not validate_meeting_id(meeting_id):
            errors.append(f"{relpath(path, root)}: meeting_id must match MTG-YYYYMMDD-NNN")
    for data_path in _minutes_data_files(root):
        data = json.loads(data_path.read_text(encoding="utf-8"))
        meeting_id = str(data.get("meeting_id") or data_path.parents[1].name)
        if not validate_meeting_id(meeting_id):
            errors.append(f"{relpath(data_path, root)}: meeting_id must match MTG-YYYYMMDD-NNN")
        for group in ("decisions", "actions", "issues"):
            for item in data.get(group, []):
                item_id = str(item.get("id", ""))
                if item_id and not validate_derived_id(item_id):
                    errors.append(f"{relpath(data_path, root)}: {item_id} must use derived ID format")
        main_path = root / "25_Meetings" / meeting_id / f"{meeting_id}.md"
        if main_path.exists():
            frontmatter = parse_frontmatter(main_path.read_text(encoding="utf-8"))
            if not validate_meeting_id(str(frontmatter.get("meeting_id", ""))):
                errors.append(f"{relpath(main_path, root)}: meeting_id must match MTG-YYYYMMDD-NNN")
    return errors


def _check_generated_blocks(root: Path) -> List[str]:
    errors: List[str] = []
    for path in sorted(root.glob("**/*.md")):
        if any(part in {".git", ".workflow", ".pytest_cache"} for part in path.parts):
            continue
        errors.extend(generated_block_errors(path.read_text(encoding="utf-8"), relpath(path, root)))
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render and validate manual GPT meeting repository artifacts.")
    parser.add_argument("--root", type=Path, default=repo_root_from(), help="09_Meeting repository root.")
    parser.add_argument("--meeting-id", default="")
    parser.add_argument("--validate", action="store_true", help="Run validation after rendering plan.")
    parser.add_argument("--apply", action="store_true", help="Write files. Defaults to dry run.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    actions = render_repo(args.root, meeting_id=args.meeting_id, apply=args.apply)
    print("APPLY" if args.apply else "DRY RUN")
    for action in actions:
        print(f"- {action}")
    if args.validate:
        errors = validate_repo(args.root)
        if errors:
            print("VALIDATION FAILED")
            for error in errors:
                print(f"- {error}")
            return 1
        print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
