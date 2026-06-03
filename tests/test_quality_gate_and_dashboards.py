from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from import_gpt_minutes import expected_gpt_output_path, import_gpt_minutes
from quality_gate import quality_gate
from register_source import register_source
from update_dashboards import update_dashboards


MEETING_ID = "MTG-20260601-001"


def copy_template(root: Path) -> None:
    target = root / "90_Templates" / "meeting_main_template.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "90_Templates" / "meeting_main_template.md", target)


def build_imported_meeting(root: Path) -> None:
    copy_template(root)
    register_source(root, MEETING_ID, "Demo", "2026-06-01", apply=True)
    output = expected_gpt_output_path(root, MEETING_ID)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
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
    import_gpt_minutes(root, MEETING_ID, gpt_output=output, apply=False)
    import_gpt_minutes(root, MEETING_ID, gpt_output=output, apply=True)


def test_dashboards_write_required_targets(tmp_path: Path) -> None:
    build_imported_meeting(tmp_path)

    actions = update_dashboards(tmp_path, apply=True)

    assert any("Meeting_HOME.md" in action for action in actions)
    assert any("Action_Queue.md" in action for action in actions)
    assert any("Decision_Register.md" in action for action in actions)
    assert (tmp_path / "00_Dashboard" / "Meeting_HOME.md").exists()
    assert (tmp_path / "00_Dashboard" / "Action_Queue.md").exists()
    assert (tmp_path / "00_Dashboard" / "Decision_Register.md").exists()


def test_quality_gate_requires_dashboards_after_import(tmp_path: Path) -> None:
    build_imported_meeting(tmp_path)

    errors = quality_gate(tmp_path)

    assert any("missing dashboard target" in error for error in errors)

    update_dashboards(tmp_path, apply=True)
    assert quality_gate(tmp_path) == []
