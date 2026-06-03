from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from meeting_workflow_state import (
    normalize_meeting_date,
    normalize_relpath,
    parse_frontmatter,
    relpath,
    repo_root_from,
    require_valid_meeting_id,
    validate_meeting_id_in_path,
    write_text,
)


GPT_OUTPUT_PLACEHOLDER = "<!-- Paste ChatGPT output below this line. Do not paste raw STT here. -->"
TEXT_EXTENSIONS = {".csv", ".log", ".markdown", ".md", ".srt", ".tsv", ".txt", ".vtt"}
AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".mp4", ".wav", ".webm"}


@dataclass
class MeetingContext:
    meeting_id: str
    title: str
    meeting_date: str
    source_note: Path
    main_note: Path
    raw_ref: str
    raw_archived: bool


def gpt_input_path(root: Path, meeting_id: str) -> Path:
    return root.resolve() / "40_Work" / f"{require_valid_meeting_id(meeting_id)}_gpt_input.md"


def gpt_output_path(root: Path, meeting_id: str) -> Path:
    return root.resolve() / "40_Work" / f"{require_valid_meeting_id(meeting_id)}_gpt_output.md"


def generate_gpt_input(
    root: Path,
    meeting_id: str,
    title: str = "",
    meeting_date: str = "",
    source_file: Optional[Path] = None,
    apply: bool = False,
) -> List[str]:
    root = root.resolve()
    meeting_id = require_valid_meeting_id(meeting_id)
    context = _load_context(root, meeting_id, title=title, meeting_date=meeting_date)
    source_path = _validated_optional_file(source_file, meeting_id)
    stt_path = _find_stt_file(root, context.raw_ref, source_path)
    if stt_path is None:
        raise ValueError(
            "No readable STT text file was found. Register or select a text/STT file before generating GPT input."
        )
    validate_meeting_id_in_path(stt_path, meeting_id, "STT path")

    stt_text = _clean_stt_text(_read_text_file(stt_path), stt_path.suffix.lower())
    if not stt_text.strip():
        raise ValueError(f"STT file is empty after cleaning: {stt_path}")
    input_text = _render_gpt_input(root, context, stt_path, stt_text, source_path)
    actions = [write_text(gpt_input_path(root, meeting_id), input_text, apply=apply)]
    actions.append(_reserve_gpt_output(gpt_output_path(root, meeting_id), apply=apply))
    return actions


def _load_context(root: Path, meeting_id: str, title: str = "", meeting_date: str = "") -> MeetingContext:
    main_note = root / "25_Meetings" / meeting_id / f"{meeting_id}.md"
    if not main_note.exists():
        raise FileNotFoundError(f"Missing main meeting note. Register raw/STT first: {main_note}")
    main_fm = parse_frontmatter(main_note.read_text(encoding="utf-8"))
    source_note = _source_note_path(root, meeting_id, main_fm)
    if not source_note.exists():
        raise FileNotFoundError(f"Missing source note. Register raw/STT first: {source_note}")
    source_fm = parse_frontmatter(source_note.read_text(encoding="utf-8"))
    resolved_title = str(title or main_fm.get("title") or source_fm.get("title") or meeting_id).strip()
    resolved_date = str(meeting_date or main_fm.get("meeting_date") or source_fm.get("meeting_date") or "").strip()
    raw_ref = str(source_fm.get("raw_source") or main_fm.get("source_raw") or "Not provided").strip()
    return MeetingContext(
        meeting_id=meeting_id,
        title=resolved_title,
        meeting_date=normalize_meeting_date(resolved_date),
        source_note=source_note,
        main_note=main_note,
        raw_ref=raw_ref,
        raw_archived=bool(source_fm.get("raw_archived")),
    )


def _source_note_path(root: Path, meeting_id: str, main_fm: Dict[str, Any]) -> Path:
    source_rel = normalize_relpath(str(main_fm.get("source_note") or ""))
    if source_rel:
        return root / source_rel
    return root / "20_Sources" / f"{meeting_id}_source.md"


def _validated_optional_file(path: Optional[Path], meeting_id: str) -> Optional[Path]:
    if path is None:
        return None
    resolved = path.expanduser().resolve()
    validate_meeting_id_in_path(resolved, meeting_id, "Source/STT/audio path")
    if not resolved.exists():
        raise FileNotFoundError(f"Source/STT file does not exist: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"Source/STT path must be a file, not a directory: {resolved}")
    return resolved


def _find_stt_file(root: Path, raw_ref: str, source_file: Optional[Path]) -> Optional[Path]:
    candidates: List[Path] = []
    if source_file is not None:
        candidates.append(source_file)
    raw_path = _resolve_raw_ref(root, raw_ref)
    if raw_path is not None:
        candidates.append(raw_path)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and candidate.suffix.lower() in TEXT_EXTENSIONS:
            return candidate
    return None


def _resolve_raw_ref(root: Path, raw_ref: str) -> Optional[Path]:
    text = str(raw_ref or "").strip()
    if not text or text.lower() in {"not provided", "not_available", "none"}:
        return None
    if text.startswith("external:"):
        return Path(text[len("external:") :]).expanduser()
    path = Path(text).expanduser()
    return path if path.is_absolute() else root / path


def _read_text_file(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _clean_stt_text(text: str, suffix: str) -> str:
    if suffix not in {".srt", ".vtt"}:
        return text.strip()
    cleaned: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.upper() == "WEBVTT" or line.upper().startswith("NOTE"):
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if re.search(r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}[,.]\d{3}", line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _render_gpt_input(
    root: Path,
    context: MeetingContext,
    stt_path: Path,
    stt_text: str,
    source_file: Optional[Path],
) -> str:
    raw_archive = _raw_archive_ref(root, context)
    audio_file = _audio_ref(root, context.raw_ref, source_file)
    return f"""# GPT 입력 파일 - {context.meeting_id}

## 1. 회의 메타데이터
- meeting_id: {context.meeting_id}
- title: {context.title}
- date: {context.meeting_date}
- source_note: {relpath(context.source_note, root)}
- raw_archive: {raw_archive}
- stt_file: {_display_path(stt_path, root)}
- audio_file: {audio_file}
- speaker_reliable: false
- role_reliable: false

## 2. 작업 규칙
- 이 파일 전체를 ChatGPT에 붙여넣고 결과를 `{relpath(gpt_output_path(root, context.meeting_id), root)}`에 저장한다.
- 프로그램은 OpenAI API를 호출하지 않으며 API 키를 요구하지 않는다.
- 원문에 없는 내용은 작성하지 마라.
- Galaxy STT 화자 구분은 신뢰하지 마라.
- 화자, 직책, 담당자, 결정권자는 명확한 원문 근거가 있을 때만 확정하라.
- 불확실하면 "확인 필요" 또는 review_required로 표시하라.
- 확정 표현이 없으면 Decision으로 분류하지 마라.
- "검토", "추후 확인", "논의 필요"는 Open Issue로 분류하라.
- 담당자나 기한이 불명확한 Action은 확정하지 말고 review_required로 표시하라.
- 회의 전체 Main Meeting Note를 먼저 작성한 뒤 Decision / Action / Open Issue 후보를 분리하라.

## 3. 출력 형식
아래 섹션명을 그대로 유지하라.

### Main Meeting Note

### Decision 후보
| ID | 제목 | 결정 내용 | 근거 | 확인 필요 |
|---|---|---|---|---|

### Action 후보
| ID | 할 일 | 담당자 | 기한 | 근거 | 확인 필요 |
|---|---|---|---|---|---|

### Open Issue 후보
| ID | 이슈 | 확인 주체 | 근거 | 다음 조치 |
|---|---|---|---|---|

### 검토 필요 항목
| 위치 | 검토 사유 | 확인할 내용 |
|---|---|---|

## 4. STT 원문
```text
{stt_text}
```
"""


def _raw_archive_ref(root: Path, context: MeetingContext) -> str:
    raw_path = _resolve_raw_ref(root, context.raw_ref)
    if not raw_path or str(context.raw_ref).startswith("external:"):
        return "not_available"
    archive = root / "20_Sources" / "00_Originals"
    try:
        raw_path.resolve().relative_to(archive.resolve())
    except ValueError:
        return "not_available"
    return relpath(raw_path, root)


def _audio_ref(root: Path, raw_ref: str, source_file: Optional[Path]) -> str:
    candidates = [path for path in (source_file, _resolve_raw_ref(root, raw_ref)) if path is not None]
    for candidate in candidates:
        if candidate.suffix.lower() in AUDIO_EXTENSIONS:
            return _display_path(candidate, root)
    return "not_available"


def _display_path(path: Path, root: Path) -> str:
    if _is_under_root(path, root):
        return relpath(path, root)
    return f"external:{path.as_posix()}"


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
    except FileNotFoundError:
        return False


def _reserve_gpt_output(path: Path, apply: bool) -> str:
    if path.exists() and not path.is_file():
        raise ValueError(f"GPT output path must be a file, not a directory: {path}")
    if path.exists():
        return f"unchanged existing GPT output file {path}"
    text = GPT_OUTPUT_PLACEHOLDER + "\n"
    return write_text(path, text, apply=apply)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a manual ChatGPT input file for a registered meeting.")
    parser.add_argument("--root", type=Path, default=repo_root_from(), help="09_Meeting repository root.")
    parser.add_argument("--meeting-id", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--date", default="")
    parser.add_argument("--source-file", type=Path, help="Optional selected raw/STT file from the launcher.")
    parser.add_argument("--apply", action="store_true", help="Write files. Defaults to dry run.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    actions = generate_gpt_input(
        root=args.root,
        meeting_id=args.meeting_id,
        title=args.title,
        meeting_date=args.date,
        source_file=args.source_file,
        apply=args.apply,
    )
    print("APPLY" if args.apply else "DRY RUN")
    for action in actions:
        print(f"- {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
