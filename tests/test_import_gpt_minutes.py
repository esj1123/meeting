from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from import_gpt_minutes import expected_gpt_output_path, import_gpt_minutes
from register_source import register_source


MEETING_ID = "MTG-20260601-001"


def copy_template(root: Path) -> None:
    target = root / "90_Templates" / "meeting_main_template.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text((ROOT / "90_Templates" / "meeting_main_template.md").read_text(encoding="utf-8"), encoding="utf-8")


def register_meeting(root: Path) -> None:
    copy_template(root)
    register_source(root=root, meeting_id=MEETING_ID, title="Demo", meeting_date="2026-06-01", apply=True)


def fixed_output(summary: str = "출시 전 점검 항목을 검토했다.") -> str:
    return f"""### Main Meeting Note
- {summary}

### Decision 후보
| ID | 제목 | 결정 내용 | 근거 | 확인 필요 |
|---|---|---|---|---|
| D-1 | 배포 방식 | 확정 표현이 없어 결정 후보로만 남김 | 결정은 다음 회의에서 | 확인 필요 |

### Action 후보
| ID | 할 일 | 담당자 | 기한 | 근거 | 확인 필요 |
|---|---|---|---|---|---|
| A-1 | 일정 재확인 | 확인 필요 | 미정 | 추후 확인 | 확인 필요 |

### Open Issue 후보
| ID | 이슈 | 확인 주체 | 근거 | 다음 조치 |
|---|---|---|---|---|
| I-1 | 담당자 불명확 | 확인 필요 | 담당자는 추후 확인 | 다음 회의에서 확인 |

### 검토 필요 항목
| 위치 | 검토 사유 | 확인할 내용 |
|---|---|---|
| Action A-1 | 담당자와 기한 불명확 | 실제 담당자와 기한 |
"""


def write_expected_output(root: Path, text: str) -> Path:
    path = expected_gpt_output_path(root, MEETING_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def preview_then_apply(root: Path, path: Path) -> None:
    import_gpt_minutes(root, MEETING_ID, gpt_output=path, apply=False)
    import_gpt_minutes(root, MEETING_ID, gpt_output=path, apply=True)


def test_import_fixed_manual_output_requires_preview_then_creates_links(tmp_path: Path) -> None:
    register_meeting(tmp_path)
    gpt_output = write_expected_output(tmp_path, fixed_output())

    try:
        import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=gpt_output, apply=True)
    except ValueError as exc:
        assert "Run import preview before apply" in str(exc)
    else:
        raise AssertionError("Expected apply before preview to fail")

    preview = import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=gpt_output, apply=False)
    assert any("preview counts: main=1 decisions=1 actions=1 open_issues=1 review_required=3" in action for action in preview)
    assert any("warning: action" in action for action in preview)

    actions = import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=gpt_output, apply=True)
    assert any("gpt_minutes.json" in action for action in actions)
    main = tmp_path / "25_Meetings" / MEETING_ID / f"{MEETING_ID}.md"
    main_text = main.read_text(encoding="utf-8")
    assert "decisions/DEC-20260601-001-001.md" in main_text
    assert "actions/ACT-20260601-001-001.md" in main_text
    assert "issues/ISS-20260601-001-001.md" in main_text

    data = json.loads((tmp_path / "25_Meetings" / MEETING_ID / "_data" / "gpt_minutes.json").read_text(encoding="utf-8"))
    assert data["title"] == "Demo"
    assert data["summary"] == ["출시 전 점검 항목을 검토했다."]
    assert data["decisions"][0]["id"] == "DEC-20260601-001-001"
    assert data["actions"][0]["task"] == "일정 재확인"
    assert data["actions"][0]["owner"] == "Unknown"
    assert data["actions"][0]["due"] == "Unknown"
    assert data["actions"][0]["review_required"] is True
    assert data["issues"][0]["issue"] == "담당자 불명확"

    action_note = tmp_path / "25_Meetings" / MEETING_ID / "actions" / "ACT-20260601-001-001.md"
    action_text = action_note.read_text(encoding="utf-8")
    assert "type: issue" in action_text
    assert "issue_subtype: action" in action_text
    assert "workflow/action" in action_text


def test_reimport_preserves_manual_content(tmp_path: Path) -> None:
    register_meeting(tmp_path)
    gpt_output = write_expected_output(tmp_path, fixed_output("First"))
    preview_then_apply(tmp_path, gpt_output)

    main = tmp_path / "25_Meetings" / MEETING_ID / f"{MEETING_ID}.md"
    text = main.read_text(encoding="utf-8").replace("Add user-authored notes here.", "Manual owner note.")
    main.write_text(text, encoding="utf-8")

    gpt_output.write_text(fixed_output("Second"), encoding="utf-8")
    preview_then_apply(tmp_path, gpt_output)
    updated = main.read_text(encoding="utf-8")
    assert "Manual owner note." in updated
    assert "Second" in updated
    assert "First" not in updated


def test_import_rejects_invalid_gpt_output_paths_and_content(tmp_path: Path) -> None:
    register_meeting(tmp_path)
    cases = [
        ("empty path", Path(""), "cannot be empty"),
        ("dot path", Path("."), "cannot be empty"),
        ("missing", expected_gpt_output_path(tmp_path, MEETING_ID), "does not exist"),
    ]
    for _label, path, expected in cases:
        try:
            import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=path, apply=False)
        except (FileNotFoundError, ValueError) as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"Expected {path} to fail")

    expected_path = expected_gpt_output_path(tmp_path, MEETING_ID)
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.mkdir()
    try:
        import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=expected_path, apply=False)
    except ValueError as exc:
        assert "not a directory" in str(exc)
    else:
        raise AssertionError("Expected directory GPT output to fail")
    expected_path.rmdir()

    wrong_ext = tmp_path / "40_Work" / f"{MEETING_ID}_gpt_output.txt"
    wrong_ext.write_text(fixed_output(), encoding="utf-8")
    try:
        import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=wrong_ext, apply=False)
    except ValueError as exc:
        assert ".md" in str(exc)
    else:
        raise AssertionError("Expected non-.md GPT output to fail")

    wrong_name = tmp_path / "40_Work" / "other_gpt_output.md"
    wrong_name.write_text(fixed_output(), encoding="utf-8")
    try:
        import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=wrong_name, apply=False)
    except ValueError as exc:
        assert f"{MEETING_ID}_gpt_output.md" in str(exc)
    else:
        raise AssertionError("Expected wrong GPT output filename to fail")

    mismatch = tmp_path / "40_Work" / "MTG-20260602-001_gpt_output.md"
    mismatch.write_text(fixed_output(), encoding="utf-8")
    try:
        import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=mismatch, apply=False)
    except ValueError as exc:
        assert "different meeting_id" in str(exc)
    else:
        raise AssertionError("Expected mismatched meeting ID in GPT output path to fail")

    expected_path.write_text("", encoding="utf-8")
    try:
        import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=expected_path, apply=False)
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("Expected empty GPT output to fail")

    expected_path.write_text("### Main Meeting Note\n- only one section\n", encoding="utf-8")
    try:
        import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=expected_path, apply=False)
    except ValueError as exc:
        assert "missing required fixed sections" in str(exc)
    else:
        raise AssertionError("Expected missing sections to fail")


def test_import_rejects_raw_stt_as_gpt_output(tmp_path: Path) -> None:
    register_meeting(tmp_path)
    gpt_output = write_expected_output(
        tmp_path,
        "화자 1: 원본 STT입니다.\n화자 2: 아직 ChatGPT 결과가 아닙니다.",
    )
    try:
        import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=gpt_output, apply=False)
    except ValueError as exc:
        assert "missing required fixed sections" in str(exc)
    else:
        raise AssertionError("Expected raw STT import to fail")


def test_apply_rejects_changed_output_after_preview(tmp_path: Path) -> None:
    register_meeting(tmp_path)
    gpt_output = write_expected_output(tmp_path, fixed_output("First"))
    import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=gpt_output, apply=False)
    gpt_output.write_text(fixed_output("Changed after preview"), encoding="utf-8")
    try:
        import_gpt_minutes(tmp_path, MEETING_ID, gpt_output=gpt_output, apply=True)
    except ValueError as exc:
        assert "changed after preview" in str(exc)
    else:
        raise AssertionError("Expected changed GPT output to require a new preview")
