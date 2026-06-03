from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from meeting_workflow_state import (
    markdown_bullets,
    markdown_table,
    normalize_minutes,
    parse_frontmatter,
    require_valid_meeting_id,
    relpath,
    replace_blocks_in_file,
    repo_root_from,
    review_required_for_item,
    write_text,
)


def parse_gpt_output(text: str, meeting_id: str) -> Dict[str, Any]:
    meeting_id = require_valid_meeting_id(meeting_id)
    json_text = _extract_json(text)
    if json_text:
        data = json.loads(json_text)
        data["meeting_id"] = meeting_id
        return normalize_minutes(data, meeting_id)
    data = _parse_markdown_sections(text, meeting_id)
    data["meeting_id"] = meeting_id
    return normalize_minutes(data, meeting_id)


def import_gpt_minutes(
    root: Path,
    meeting_id: str,
    gpt_output: Optional[Path] = None,
    gpt_text: Optional[str] = None,
    apply: bool = False,
) -> List[str]:
    root = root.resolve()
    if gpt_text is None:
        if gpt_output is None:
            raise ValueError("Either gpt_output or gpt_text is required.")
        if not gpt_output.exists():
            raise FileNotFoundError(f"GPT output file does not exist: {gpt_output}")
        if not gpt_output.is_file():
            raise ValueError(f"GPT output path must be a file, not a directory: {gpt_output}")
        gpt_text = gpt_output.read_text(encoding="utf-8")
    minutes = parse_gpt_output(gpt_text, meeting_id)
    minutes = _apply_main_note_metadata(root, meeting_id, minutes)
    return render_minutes_artifacts(root=root, meeting_id=meeting_id, minutes=minutes, apply=apply)


def render_minutes_artifacts(root: Path, meeting_id: str, minutes: Dict[str, Any], apply: bool = False) -> List[str]:
    root = root.resolve()
    meeting_id = require_valid_meeting_id(meeting_id)
    minutes["meeting_id"] = meeting_id
    minutes = normalize_minutes(minutes, meeting_id)
    meeting_id = minutes["meeting_id"]
    meeting_dir = root / "25_Meetings" / meeting_id
    main_note = meeting_dir / f"{meeting_id}.md"
    if not main_note.exists():
        raise FileNotFoundError(f"Missing main meeting note: {main_note}")
    actions: List[str] = []
    data_path = meeting_dir / "_data" / "gpt_minutes.json"
    actions.append(write_text(data_path, json.dumps(minutes, indent=2, ensure_ascii=False), apply=apply))
    actions.append(
        replace_blocks_in_file(
            main_note,
            main_note.read_text(encoding="utf-8"),
            _main_blocks(minutes),
            apply=apply,
        )
    )
    for kind, folder, items in (
        ("decision", "decisions", minutes["decisions"]),
        ("action", "actions", minutes["actions"]),
        ("issue", "issues", minutes["issues"]),
    ):
        for item in items:
            path = meeting_dir / folder / f"{item['id']}.md"
            base = _item_base(kind, meeting_id, item)
            actions.append(
                replace_blocks_in_file(
                    path,
                    base,
                    {"ITEM": _item_generated(kind, meeting_id, item)},
                    apply=apply,
                )
            )
    return actions


def _extract_json(text: str) -> Optional[str]:
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fence:
        return fence.group(1)
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    return None


def _parse_markdown_sections(text: str, meeting_id: str) -> Dict[str, Any]:
    fixed = _parse_fixed_manual_output(text, meeting_id)
    if fixed is not None:
        return fixed
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for line in text.splitlines():
        heading = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
        if heading:
            key = heading.group(1).strip().lower()
            if key in {"summary", "decisions", "actions", "issues"}:
                current = key
                sections.setdefault(current, [])
            else:
                current = None
            continue
        if current and line.strip():
            value = re.sub(r"^\s*[-*]\s+", "", line).strip()
            if value:
                sections[current].append(value)
    if not sections:
        raise ValueError(
            "GPT output does not contain recognized sections or JSON. "
            "Select the saved ChatGPT output file, not the raw/STT source file."
        )
    return {
        "meeting_id": meeting_id,
        "summary": sections.get("summary", []),
        "decisions": [{"title": item} for item in sections.get("decisions", [])],
        "actions": [{"task": item} for item in sections.get("actions", [])],
        "issues": [{"issue": item} for item in sections.get("issues", [])],
    }


def _parse_fixed_manual_output(text: str, meeting_id: str) -> Optional[Dict[str, Any]]:
    sections = _sections_by_heading(text)
    main_lines = _section_by_name(sections, "main meeting note")
    decision_lines = _section_by_name(sections, "decision 후보")
    action_lines = _section_by_name(sections, "action 후보")
    issue_lines = _section_by_name(sections, "open issue 후보")
    review_lines = _section_by_name(sections, "검토 필요 항목")
    if all(value is None for value in (main_lines, decision_lines, action_lines, issue_lines, review_lines)):
        return None
    review_reasons = [
        _review_reason_from_row(row)
        for row in _parse_markdown_table(review_lines or [])
        if _review_reason_from_row(row)
    ]
    return {
        "meeting_id": meeting_id,
        "summary": _summary_lines(main_lines or []),
        "decisions": [_decision_from_row(row) for row in _parse_markdown_table(decision_lines or [])],
        "actions": [_action_from_row(row) for row in _parse_markdown_table(action_lines or [])],
        "issues": [_issue_from_row(row) for row in _parse_markdown_table(issue_lines or [])],
        "review": {
            "review_required": bool(review_reasons),
            "reasons": review_reasons,
        },
    }


def _sections_by_heading(text: str) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for line in text.splitlines():
        heading = re.match(r"^#{1,4}\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1).strip().lower()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def _section_by_name(sections: Dict[str, List[str]], name: str) -> Optional[List[str]]:
    return sections.get(name.lower())


def _summary_lines(lines: List[str]) -> List[str]:
    result: List[str] = []
    for line in lines:
        value = re.sub(r"^\s*[-*]\s+", "", line).strip()
        if not value or value.startswith("<!--") or value.startswith("|"):
            continue
        result.append(value)
    return result


def _parse_markdown_table(lines: List[str]) -> List[Dict[str, str]]:
    table_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
        elif table_lines:
            break
    if len(table_lines) < 2:
        return []
    headers = _split_table_row(table_lines[0])
    rows: List[Dict[str, str]] = []
    for line in table_lines[2:]:
        cells = _split_table_row(line)
        if not any(cells):
            continue
        rows.append({header: cells[index] if index < len(cells) else "" for index, header in enumerate(headers)})
    return rows


def _split_table_row(line: str) -> List[str]:
    body = line.strip().strip("|")
    return [cell.replace("\\|", "|").strip() for cell in re.split(r"(?<!\\)\|", body)]


def _decision_from_row(row: Dict[str, str]) -> Dict[str, Any]:
    title = _row_value(row, "제목", "title") or _row_value(row, "결정 내용", "decision")
    content = _row_value(row, "결정 내용", "decision")
    evidence = _row_value(row, "근거", "evidence", "source_refs")
    return {
        "id": _row_value(row, "ID", "id"),
        "title": title,
        "decision": content,
        "source_refs": [evidence] if evidence else [],
        "review_required": _review_required(_row_value(row, "확인 필요", "review_required"), title, content),
    }


def _action_from_row(row: Dict[str, str]) -> Dict[str, Any]:
    owner = _row_value(row, "담당자", "owner")
    due = _row_value(row, "기한", "due")
    evidence = _row_value(row, "근거", "evidence", "source_refs")
    task = _row_value(row, "할 일", "action", "task")
    return {
        "id": _row_value(row, "ID", "id"),
        "task": task,
        "owner": _unknown_if_uncertain(owner),
        "due": _unknown_if_uncertain(due),
        "source_refs": [evidence] if evidence else [],
        "review_required": _review_required(_row_value(row, "확인 필요", "review_required"), owner, due, task),
    }


def _issue_from_row(row: Dict[str, str]) -> Dict[str, Any]:
    owner = _row_value(row, "확인 주체", "owner")
    evidence = _row_value(row, "근거", "evidence", "source_refs")
    next_action = _row_value(row, "다음 조치", "next_action")
    issue = _row_value(row, "이슈", "issue")
    return {
        "id": _row_value(row, "ID", "id"),
        "issue": issue,
        "owner": _unknown_if_uncertain(owner),
        "next_action": next_action,
        "source_refs": [evidence] if evidence else [],
        "review_required": _review_required(owner, next_action),
    }


def _row_value(row: Dict[str, str], *keys: str) -> str:
    lowered = {key.lower(): value for key, value in row.items()}
    for key in keys:
        if key in row:
            return row[key].strip()
        value = lowered.get(key.lower())
        if value is not None:
            return value.strip()
    return ""


def _review_reason_from_row(row: Dict[str, str]) -> str:
    location = _row_value(row, "위치", "location")
    reason = _row_value(row, "검토 사유", "reason")
    required = _row_value(row, "확인할 내용", "check")
    parts = [part for part in (location, reason, required) if part]
    return ": ".join(parts)


def _review_required(*values: str) -> bool:
    return any(_uncertain(value) for value in values)


def _unknown_if_uncertain(value: str) -> str:
    return "Unknown" if _uncertain(value) else value


def _uncertain(value: str) -> bool:
    text = str(value or "").strip()
    lowered = text.lower()
    if not text:
        return True
    if lowered in {"yes", "true", "review_required", "review required", "tbd", "unknown", "unclear", "not specified"}:
        return True
    if lowered in {"no", "false", "none", "n/a"}:
        return False
    if "불필요" in text:
        return False
    return any(marker in text for marker in ("확인 필요", "불명확", "미정", "추후 확인"))


def _apply_main_note_metadata(root: Path, meeting_id: str, minutes: Dict[str, Any]) -> Dict[str, Any]:
    main_note = root.resolve() / "25_Meetings" / meeting_id / f"{meeting_id}.md"
    if not main_note.exists():
        return minutes
    frontmatter = parse_frontmatter(main_note.read_text(encoding="utf-8"))
    if frontmatter.get("title") and str(minutes.get("title", "")).strip() in {"", meeting_id}:
        minutes["title"] = frontmatter["title"]
    if frontmatter.get("meeting_date") and str(minutes.get("meeting_date", "")).strip() in {"", "Unknown"}:
        minutes["meeting_date"] = frontmatter["meeting_date"]
    return minutes


def _main_blocks(minutes: Dict[str, Any]) -> Dict[str, str]:
    return {
        "SUMMARY": markdown_bullets(minutes["summary"]),
        "DECISIONS": _decision_table(minutes["decisions"]),
        "ACTIONS": _action_table(minutes["actions"]),
        "ISSUES": _issue_table(minutes["issues"]),
        "REVIEW": _review_block(minutes),
    }


def _decision_table(items: List[Dict[str, Any]]) -> str:
    rows = [
        [
            f"[{item['id']}](decisions/{item['id']}.md)",
            item.get("title", ""),
            item.get("decider", "Unknown"),
            item.get("owner", "Unknown"),
            item.get("due", "Unknown"),
            "yes" if item.get("review_required") else "no",
        ]
        for item in items
    ]
    return markdown_table(["ID", "Decision", "Decider", "Owner", "Due", "Review"], rows)


def _action_table(items: List[Dict[str, Any]]) -> str:
    rows = [
        [
            f"[{item['id']}](actions/{item['id']}.md)",
            item.get("task", ""),
            item.get("owner", "Unknown"),
            item.get("due", "Unknown"),
            "yes" if item.get("review_required") else "no",
        ]
        for item in items
    ]
    return markdown_table(["ID", "Action", "Owner", "Due", "Review"], rows)


def _issue_table(items: List[Dict[str, Any]]) -> str:
    rows = [
        [
            f"[{item['id']}](issues/{item['id']}.md)",
            item.get("issue", ""),
            item.get("owner", "Unknown"),
            "yes" if item.get("review_required") else "no",
        ]
        for item in items
    ]
    return markdown_table(["ID", "Issue", "Owner", "Review"], rows)


def _review_block(minutes: Dict[str, Any]) -> str:
    rows: List[List[str]] = []
    for kind, field in (("decision", "title"), ("action", "task"), ("issue", "issue")):
        group = f"{kind}s" if kind != "action" else "actions"
        for item in minutes[group]:
            if item.get("review_required") or review_required_for_item(kind, item):
                rows.append([kind, item["id"], item.get(field, ""), _review_reason(kind, item)])
    return markdown_table(["Kind", "ID", "Item", "Reason"], rows)


def _review_reason(kind: str, item: Dict[str, Any]) -> str:
    missing = []
    for field in ("owner", "decider", "due"):
        if field in item and review_required_for_item(kind, {field: item.get(field), **item}):
            if str(item.get(field, "")).strip().lower() in {"", "unknown", "tbd", "unclear", "not specified"}:
                missing.append(field)
    return "Confirm " + ", ".join(missing or ["uncertain fields"])


def _item_base(kind: str, meeting_id: str, item: Dict[str, Any]) -> str:
    item_id = item["id"]
    title = item.get("title") or item.get("task") or item.get("issue") or item_id
    if kind == "action":
        type_lines = "\n".join(
            [
                "type: issue",
                "issue_subtype: action",
                f'action_id: "{item_id}"',
                f'parent_meeting: "{meeting_id}"',
                "tags:",
                "  - workflow/action",
            ]
        )
    elif kind == "decision":
        type_lines = "\n".join(
            [
                "type: decision",
                f'decision_id: "{item_id}"',
                f'parent_meeting: "{meeting_id}"',
            ]
        )
    else:
        type_lines = "\n".join(
            [
                "type: issue",
                f'issue_id: "{item_id}"',
                f'parent_meeting: "{meeting_id}"',
            ]
        )
    return f"""---
{type_lines}
meeting_id: "{meeting_id}"
item_id: "{item_id}"
meeting_note: "../{meeting_id}.md"
review_required: {str(bool(item.get("review_required"))).lower()}
---

# {item_id}: {title}

<!-- AUTO-GENERATED: ITEM START -->
Pending render.
<!-- AUTO-GENERATED: ITEM END -->

## Manual Notes

"""


def _item_generated(kind: str, meeting_id: str, item: Dict[str, Any]) -> str:
    if kind == "decision":
        lines = [
            f"- Decision: {item.get('title', '')}",
            f"- Decider: {item.get('decider', 'Unknown')}",
            f"- Owner: {item.get('owner', 'Unknown')}",
            f"- Due: {item.get('due', 'Unknown')}",
        ]
    elif kind == "action":
        lines = [
            f"- Action: {item.get('task', '')}",
            f"- Owner: {item.get('owner', 'Unknown')}",
            f"- Due: {item.get('due', 'Unknown')}",
        ]
    else:
        lines = [
            f"- Issue: {item.get('issue', '')}",
            f"- Owner: {item.get('owner', 'Unknown')}",
        ]
    lines.append(f"- Review required: {'yes' if item.get('review_required') else 'no'}")
    lines.append(f"- Meeting note: [back](../{meeting_id}.md)")
    refs = item.get("source_refs", [])
    if refs:
        lines.append("- Source refs:")
        lines.extend(f"  - {ref}" for ref in refs)
    return "\n".join(lines)


def meeting_id_from_main_note(path: Path) -> str:
    frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
    return str(frontmatter.get("meeting_id") or path.stem)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import pasted manual GPT meeting output.")
    parser.add_argument("--root", type=Path, default=repo_root_from(), help="09_Meeting repository root.")
    parser.add_argument("--meeting-id")
    parser.add_argument("--main-note", type=Path)
    parser.add_argument("--gpt-output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Write files. Defaults to dry run.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    meeting_id = args.meeting_id
    if not meeting_id and args.main_note:
        meeting_id = meeting_id_from_main_note(args.main_note)
    if not meeting_id:
        raise SystemExit("--meeting-id or --main-note is required")
    actions = import_gpt_minutes(
        root=args.root,
        meeting_id=meeting_id,
        gpt_output=args.gpt_output,
        apply=args.apply,
    )
    print("APPLY" if args.apply else "DRY RUN")
    for action in actions:
        print(f"- {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
