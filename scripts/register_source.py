from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path
from typing import List, Optional

from meeting_workflow_state import (
    ensure_meeting_id,
    is_relative_to,
    normalize_meeting_date,
    registry_action,
    registry_has_meeting_id,
    relpath,
    repo_root_from,
    split_meeting_id,
    write_text,
)


def register_source(
    root: Path,
    meeting_id: str,
    title: str,
    meeting_date: str,
    source_file: Optional[Path] = None,
    copy_raw: bool = False,
    confirm_copy: bool = False,
    apply: bool = False,
) -> List[str]:
    root = root.resolve()
    meeting_date = normalize_meeting_date(meeting_date)
    meeting_id = ensure_meeting_id(root, meeting_id, meeting_date)
    source_id = f"{meeting_id}_source"
    source_note = root / "20_Sources" / f"{source_id}.md"
    main_note = root / "25_Meetings" / meeting_id / f"{meeting_id}.md"
    archive_dir = root / "20_Sources" / "00_Originals"
    planned: List[str] = []

    if registry_has_meeting_id(root, meeting_id) and not source_note.exists() and not main_note.exists():
        raise ValueError(f"{meeting_id} is already recorded in the registry and cannot be reused.")

    raw_ref = "Not provided"
    raw_archived = False
    copy_from: Optional[Path] = None
    copy_to: Optional[Path] = None

    if source_file:
        source_file = source_file.expanduser().resolve()
        if not source_file.exists():
            raise FileNotFoundError(f"Source file does not exist: {source_file}")
        if not source_file.is_file():
            raise ValueError(f"Source path must be a file, not a directory: {source_file}")
        if is_relative_to(source_file, root) and not is_relative_to(source_file, archive_dir):
            raise ValueError(
                "Raw source files inside this repository must already be under "
                "20_Sources/00_Originals or be copied there explicitly."
            )
        if copy_raw:
            if apply and not confirm_copy:
                raise ValueError("Copying raw files requires explicit confirmation.")
            copy_from = source_file
            copy_to = _unique_destination(archive_dir, source_file.name)
            raw_ref = relpath(copy_to, root)
            raw_archived = True
        elif is_relative_to(source_file, archive_dir):
            raw_ref = relpath(source_file, root)
            raw_archived = True
        else:
            raw_ref = f"external:{source_file}"

    if copy_from and copy_to:
        if apply:
            copy_to.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(copy_from, copy_to)
            planned.append(f"copied raw source to {copy_to}")
        else:
            planned.append(f"would copy raw source to {copy_to}")

    planned.append(registry_action(root, meeting_id, title, meeting_date, apply=apply))

    source_rel = relpath(source_note, root)
    main_rel = relpath(main_note, root)
    if source_note.exists():
        planned.append(f"unchanged existing source note {source_note}")
    else:
        source_text = _source_note_text(
            source_id=source_id,
            meeting_id=meeting_id,
            title=title,
            meeting_date=meeting_date,
            main_rel=main_rel,
            raw_ref=raw_ref,
            raw_archived=raw_archived,
        )
        planned.append(write_text(source_note, source_text, apply=apply))

    template_path = root / "90_Templates" / "meeting_main_template.md"
    if not template_path.exists():
        raise FileNotFoundError(f"Missing meeting template: {template_path}")
    if main_note.exists():
        planned.append(f"unchanged existing main note {main_note}")
    else:
        template = template_path.read_text(encoding="utf-8")
        main_text = _render_template(template, meeting_id, title, meeting_date, source_rel, raw_ref)
        planned.append(write_text(main_note, main_text, apply=apply))

    return planned


def _unique_destination(directory: Path, name: str) -> Path:
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        next_candidate = directory / f"{stem}-{index}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def _source_note_text(
    source_id: str,
    meeting_id: str,
    title: str,
    meeting_date: str,
    main_rel: str,
    raw_ref: str,
    raw_archived: bool,
) -> str:
    _date_key, meeting_seq = split_meeting_id(meeting_id)
    return f"""---
type: source
source_id: "{source_id}"
meeting_id: "{meeting_id}"
meeting_seq: "{meeting_seq}"
title: "{title}"
meeting_date: "{meeting_date}"
main_note: "{main_rel}"
raw_source: "{raw_ref}"
raw_archived: {str(raw_archived).lower()}
review_required: true
---

# Source: {title}

## Links

- Main meeting note: [{meeting_id}](../{main_rel})
- Raw source: `{raw_ref}`

## Source Policy

Raw files controlled by this repository are allowed only under `20_Sources/00_Originals/`.
"""


def _render_template(template: str, meeting_id: str, title: str, meeting_date: str, source_rel: str, raw_ref: str) -> str:
    _date_key, meeting_seq = split_meeting_id(meeting_id)
    source_link = f"[{source_rel}](../../{source_rel})"
    raw_link = f"`{raw_ref}`" if raw_ref.startswith("external:") or raw_ref == "Not provided" else f"[{raw_ref}](../../{raw_ref})"
    replacements = {
        "{{meeting_id}}": meeting_id,
        "{{meeting_seq}}": meeting_seq,
        "{{title}}": title,
        "{{meeting_date}}": meeting_date,
        "{{source_note}}": source_rel,
        "{{source_raw}}": raw_ref,
        "{{source_note_link}}": source_link,
        "{{source_raw_link}}": raw_link,
    }
    rendered = template
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    return rendered


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Register a meeting source without API automation.")
    parser.add_argument("--root", type=Path, default=repo_root_from(), help="09_Meeting repository root.")
    parser.add_argument("--meeting-id", default="", help="Defaults to the next MTG-YYYYMMDD-NNN for --date.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--copy-raw", action="store_true", help="Copy raw file into 20_Sources/00_Originals.")
    parser.add_argument("--confirm-copy", action="store_true", help="Confirm raw copy was explicitly approved.")
    parser.add_argument("--apply", action="store_true", help="Write files. Defaults to dry run.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    actions = register_source(
        root=args.root,
        meeting_id=args.meeting_id,
        title=args.title,
        meeting_date=args.date,
        source_file=args.source_file,
        copy_raw=args.copy_raw,
        confirm_copy=args.confirm_copy,
        apply=args.apply,
    )
    print("APPLY" if args.apply else "DRY RUN")
    for action in actions:
        print(f"- {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
