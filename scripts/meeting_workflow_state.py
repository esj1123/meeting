from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


GENERATED_RE = re.compile(r"<!-- AUTO-GENERATED: ([A-Z0-9_-]+) (START|END) -->")
UNKNOWN_VALUES = {"", "unknown", "tbd", "n/a", "na", "none", "null", "unclear", "not specified"}
MEETING_ID_RE = re.compile(r"^MTG-(\d{8})-(\d{3})$")
DERIVED_ID_RE = re.compile(r"^(DEC|ACT|ISS|RUN)-(\d{8})-(\d{3})-(\d{3})$")
DERIVED_PREFIXES = {
    "decision": "DEC",
    "action": "ACT",
    "issue": "ISS",
    "run": "RUN",
}


@dataclass
class WorkflowState:
    root: str
    meeting_id: str = ""
    title: str = ""
    meeting_date: str = ""
    source_file: str = ""
    gpt_output_file: str = ""
    copy_raw: bool = False

    @classmethod
    def load(cls, root: Path) -> "WorkflowState":
        path = state_path(root)
        if not path.exists():
            return cls(root=str(root))
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("root", str(root))
        return cls(**{k: data.get(k, getattr(cls(str(root)), k)) for k in cls(str(root)).__dict__})

    def save(self, root: Optional[Path] = None) -> Path:
        target_root = Path(root or self.root)
        path = state_path(target_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path


def state_path(root: Path) -> Path:
    return root / ".workflow" / "meeting_workflow_state.json"


def repo_root_from(start: Optional[Path] = None) -> Path:
    if start is not None:
        return Path(start).resolve()
    return Path(__file__).resolve().parents[1]


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_relpath(value: str) -> str:
    return value.replace("\\", "/").strip().strip('"')


def meeting_id_registry_path(root: Path) -> Path:
    return root / "40_Work" / "meeting_id_registry.jsonl"


def normalize_meeting_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        text = date.today().isoformat()
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    raise ValueError("meeting_date must use YYYY-MM-DD or YYYYMMDD.")


def meeting_date_key(value: Any) -> str:
    normalized = normalize_meeting_date(value)
    return normalized.replace("-", "")


def validate_meeting_id(value: str) -> bool:
    return bool(MEETING_ID_RE.fullmatch(str(value or "").strip()))


def require_valid_meeting_id(value: str) -> str:
    meeting_id = str(value or "").strip()
    if not validate_meeting_id(meeting_id):
        raise ValueError("meeting_id must match MTG-YYYYMMDD-NNN, for example MTG-20260602-001.")
    return meeting_id


def split_meeting_id(meeting_id: str) -> Tuple[str, str]:
    match = MEETING_ID_RE.fullmatch(require_valid_meeting_id(meeting_id))
    assert match is not None
    return match.group(1), match.group(2)


def derived_item_id(kind: str, meeting_id: str, index: int) -> str:
    date_key, meeting_seq = split_meeting_id(meeting_id)
    prefix = DERIVED_PREFIXES[kind]
    return f"{prefix}-{date_key}-{meeting_seq}-{index:03d}"


def validate_derived_id(value: str) -> bool:
    return bool(DERIVED_ID_RE.fullmatch(str(value or "").strip()))


def registry_entries(root: Path) -> List[Dict[str, Any]]:
    path = meeting_id_registry_path(root)
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            entries.append(item)
    return entries


def collect_used_meeting_ids(root: Path) -> List[str]:
    root = root.resolve()
    used = set()
    for entry in registry_entries(root):
        meeting_id = str(entry.get("meeting_id", "")).strip()
        if meeting_id:
            used.add(meeting_id)

    meetings_dir = root / "25_Meetings"
    if meetings_dir.exists():
        for meeting_dir in meetings_dir.iterdir():
            if meeting_dir.is_dir():
                used.add(meeting_dir.name)
                main_note = meeting_dir / f"{meeting_dir.name}.md"
                if main_note.exists():
                    meeting_id = parse_frontmatter(main_note.read_text(encoding="utf-8")).get("meeting_id")
                    if meeting_id:
                        used.add(str(meeting_id))
            elif meeting_dir.suffix.lower() == ".md":
                meeting_id = parse_frontmatter(meeting_dir.read_text(encoding="utf-8")).get("meeting_id")
                if meeting_id:
                    used.add(str(meeting_id))

    source_dir = root / "20_Sources"
    if source_dir.exists():
        for source_note in source_dir.glob("*.md"):
            meeting_id = parse_frontmatter(source_note.read_text(encoding="utf-8")).get("meeting_id")
            if meeting_id:
                used.add(str(meeting_id))

    return sorted(used)


def next_meeting_id(root: Path, meeting_date: Any) -> str:
    key = meeting_date_key(meeting_date)
    max_seq = 0
    for meeting_id in collect_used_meeting_ids(root):
        match = MEETING_ID_RE.fullmatch(meeting_id)
        if match and match.group(1) == key:
            max_seq = max(max_seq, int(match.group(2)))
    return f"MTG-{key}-{max_seq + 1:03d}"


def ensure_meeting_id(root: Path, meeting_id: str, meeting_date: Any) -> str:
    meeting_id = str(meeting_id or "").strip()
    if not meeting_id:
        return next_meeting_id(root, meeting_date)
    return require_valid_meeting_id(meeting_id)


def registry_has_meeting_id(root: Path, meeting_id: str) -> bool:
    return any(str(entry.get("meeting_id", "")).strip() == meeting_id for entry in registry_entries(root))


def registry_action(root: Path, meeting_id: str, title: str, meeting_date: str, apply: bool) -> str:
    meeting_id = require_valid_meeting_id(meeting_id)
    meeting_date = normalize_meeting_date(meeting_date)
    if registry_has_meeting_id(root, meeting_id):
        return f"unchanged meeting ID registry {meeting_id}"
    path = meeting_id_registry_path(root)
    entry = {
        "meeting_id": meeting_id,
        "meeting_date": meeting_date,
        "title": title,
        "status": "active",
    }
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return f"registered meeting ID {meeting_id}"
    return f"would register meeting ID {meeting_id}"


def generated_markers(name: str) -> Tuple[str, str]:
    clean = re.sub(r"[^A-Z0-9_-]+", "_", name.upper()).strip("_")
    return f"<!-- AUTO-GENERATED: {clean} START -->", f"<!-- AUTO-GENERATED: {clean} END -->"


def replace_generated_block(original: str, name: str, content: str) -> str:
    begin, end = generated_markers(name)
    body = content.rstrip()
    block = f"{begin}\n{body}\n{end}"
    if begin in original and end in original:
        start = original.index(begin)
        after_begin = start + len(begin)
        finish = original.index(end, after_begin) + len(end)
        return original[:start] + block + original[finish:]
    prefix = original
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    return prefix + "\n" + block + "\n"


def generated_block_errors(text: str, label: str = "<text>") -> List[str]:
    stack: List[str] = []
    errors: List[str] = []
    for match in GENERATED_RE.finditer(text):
        name, marker = match.group(1), match.group(2)
        if marker == "START":
            if name in stack:
                errors.append(f"{label}: nested generated block {name}")
            stack.append(name)
        else:
            if not stack:
                errors.append(f"{label}: generated block {name} ends before it starts")
            elif stack[-1] != name:
                errors.append(f"{label}: generated block {name} ends while {stack[-1]} is open")
                stack.pop()
            else:
                stack.pop()
    for name in stack:
        errors.append(f"{label}: generated block {name} has no END marker")
    return errors


def parse_frontmatter(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}
    result: Dict[str, Any] = {}
    current_key: Optional[str] = None
    for raw_line in lines[1:end_index]:
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_key:
            result.setdefault(current_key, [])
            if isinstance(result[current_key], list):
                result[current_key].append(_parse_scalar(line[4:]))
            continue
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            current_key = key.strip()
            stripped = value.strip()
            result[current_key] = [] if stripped == "" else _parse_scalar(stripped)
    return result


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in {"null", "none"}:
        return None
    return value


def slugify(value: str, fallback: str = "item") -> str:
    clean = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-")
    return clean or fallback


def unknownish(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower()
    return text in UNKNOWN_VALUES or text.endswith("?")


def review_required_for_item(kind: str, item: Dict[str, Any]) -> bool:
    kind = kind.lower()
    if kind == "decision":
        fields = ("decider", "owner", "due")
    elif kind == "action":
        fields = ("owner", "due")
    elif kind == "issue":
        fields = ("owner",)
    else:
        fields = ()
    return any(unknownish(item.get(field)) for field in fields)


def normalize_item(kind: str, item: Dict[str, Any], index: int, meeting_id: str = "") -> Dict[str, Any]:
    normalized = dict(item)
    original_id = str(normalized.get("id", "")).strip()
    if meeting_id and validate_meeting_id(meeting_id):
        normalized["id"] = derived_item_id(kind, meeting_id, index)
        if original_id and original_id != normalized["id"]:
            normalized.setdefault("source_item_id", original_id)
    else:
        prefixes = {"decision": "D", "action": "A", "issue": "I"}
        prefix = prefixes[kind]
        normalized.setdefault("id", f"{prefix}-{index:03d}")
        normalized["id"] = slugify(str(normalized["id"]), f"{prefix}-{index:03d}").upper()
    if kind == "decision":
        normalized.setdefault("title", normalized.get("text", "Untitled decision"))
        normalized.setdefault("decider", "Unknown")
        normalized.setdefault("owner", "Unknown")
        normalized.setdefault("due", "Unknown")
    elif kind == "action":
        normalized.setdefault("task", normalized.get("text", "Untitled action"))
        normalized.setdefault("owner", "Unknown")
        normalized.setdefault("due", "Unknown")
    elif kind == "issue":
        normalized.setdefault("issue", normalized.get("text", "Untitled issue"))
        normalized.setdefault("owner", "Unknown")
    refs = normalized.get("source_refs", [])
    if isinstance(refs, str):
        refs = [refs]
    normalized["source_refs"] = refs
    normalized["review_required"] = bool(normalized.get("review_required")) or review_required_for_item(kind, normalized)
    return normalized


def normalize_minutes(data: Dict[str, Any], meeting_id: str) -> Dict[str, Any]:
    normalized = dict(data)
    normalized["meeting_id"] = str(normalized.get("meeting_id") or meeting_id)
    normalized.setdefault("title", normalized["meeting_id"])
    normalized.setdefault("meeting_date", "Unknown")
    summary = normalized.get("summary", [])
    if isinstance(summary, str):
        summary = [summary]
    normalized["summary"] = [str(item) for item in summary]
    normalized["decisions"] = [
        normalize_item("decision", item, index, normalized["meeting_id"])
        for index, item in enumerate(_as_dicts(normalized.get("decisions", [])), start=1)
    ]
    normalized["actions"] = [
        normalize_item("action", item, index, normalized["meeting_id"])
        for index, item in enumerate(_as_dicts(normalized.get("actions", [])), start=1)
    ]
    normalized["issues"] = [
        normalize_item("issue", item, index, normalized["meeting_id"])
        for index, item in enumerate(_as_dicts(normalized.get("issues", [])), start=1)
    ]
    reasons = list(normalized.get("review", {}).get("reasons", [])) if isinstance(normalized.get("review"), dict) else []
    if any(item["review_required"] for group in ("decisions", "actions", "issues") for item in normalized[group]):
        if "owner_decider_due_uncertainty" not in reasons:
            reasons.append("owner_decider_due_uncertainty")
    normalized["review"] = {
        "review_required": bool(reasons),
        "reasons": reasons,
    }
    return normalized


def _as_dicts(value: Any) -> Iterable[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: List[Dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            result.append(item)
        else:
            result.append({"text": str(item)})
    return result


def write_text(path: Path, text: str, apply: bool) -> str:
    if not text.endswith("\n"):
        text += "\n"
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == text:
        return f"unchanged {path}"
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return f"wrote {path}"
    action = "would update" if old is not None else "would create"
    return f"{action} {path}"


def replace_blocks_in_file(path: Path, base_text: str, blocks: Dict[str, str], apply: bool) -> str:
    text = path.read_text(encoding="utf-8") if path.exists() else base_text
    for name, content in blocks.items():
        text = replace_generated_block(text, name, content)
    return write_text(path, text, apply=apply)


def markdown_bullets(items: Iterable[str]) -> str:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return "No items."
    return "\n".join(f"- {item}" for item in values)


def markdown_table(headers: List[str], rows: List[List[Any]]) -> str:
    if not rows:
        return "No items."
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_cell(value) for value in row) + " |" for row in rows]
    return "\n".join([header, separator] + body)


def _cell(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")
