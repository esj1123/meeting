from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from import_gpt_minutes import expected_gpt_output_path, import_gpt_minutes
from register_source import register_source
from render_meeting_repo import validate_repo


def copy_template(root: Path) -> None:
    target = root / "90_Templates" / "meeting_main_template.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text((ROOT / "90_Templates" / "meeting_main_template.md").read_text(encoding="utf-8"), encoding="utf-8")


def build_valid_sample(root: Path) -> None:
    copy_template(root)
    register_source(root, "MTG-20260601-001", "Demo", "2026-06-01", apply=True)
    gpt_file = expected_gpt_output_path(root, "MTG-20260601-001")
    gpt_file.parent.mkdir(parents=True, exist_ok=True)
    gpt_file.write_text(
        """### Main Meeting Note
- Summary

### Decision 후보
| ID | 제목 | 결정 내용 | 근거 | 확인 필요 |
|---|---|---|---|---|
| D-001 | Decision | Decision | source | no |

### Action 후보
| ID | 할 일 | 담당자 | 기한 | 근거 | 확인 필요 |
|---|---|---|---|---|---|
| A-001 | Action | B | 2026-06-10 | source | no |

### Open Issue 후보
| ID | 이슈 | 확인 주체 | 근거 | 다음 조치 |
|---|---|---|---|---|
| I-001 | Issue | B | source | monitor |
""",
        encoding="utf-8",
    )
    import_gpt_minutes(root, "MTG-20260601-001", gpt_output=gpt_file, apply=False)
    import_gpt_minutes(root, "MTG-20260601-001", gpt_output=gpt_file, apply=True)


def test_validation_accepts_complete_links(tmp_path: Path) -> None:
    build_valid_sample(tmp_path)
    assert validate_repo(tmp_path) == []


def test_validation_detects_missing_main_link(tmp_path: Path) -> None:
    build_valid_sample(tmp_path)
    main = tmp_path / "25_Meetings" / "MTG-20260601-001" / "MTG-20260601-001.md"
    main.write_text(main.read_text(encoding="utf-8").replace("actions/ACT-20260601-001-001.md", "actions/MISSING.md"), encoding="utf-8")
    errors = validate_repo(tmp_path)
    assert any("missing link to actions/ACT-20260601-001-001.md" in error for error in errors)


def test_validation_detects_raw_file_outside_archive(tmp_path: Path) -> None:
    build_valid_sample(tmp_path)
    raw = tmp_path / "loose-recording.mp3"
    raw.write_bytes(b"synthetic audio bytes")
    errors = validate_repo(tmp_path)
    assert any("raw file outside 20_Sources/00_Originals" in error for error in errors)
