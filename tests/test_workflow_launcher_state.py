from pathlib import Path
import json
import os
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from meeting_workflow_state import WorkflowState, replace_generated_block


def test_launcher_does_not_shadow_tk_register() -> None:
    import meeting_workflow_app

    assert "_register" not in meeting_workflow_app.MeetingWorkflowApp.__dict__


def test_discover_meetings_from_main_notes_and_gpt_data(tmp_path: Path) -> None:
    import meeting_workflow_app

    old_dir = tmp_path / "25_Meetings" / "MTG-20260601-001"
    old_dir.mkdir(parents=True)
    old_main = old_dir / "MTG-20260601-001.md"
    old_main.write_text(
        """---
type: knowledge
meeting_id: "MTG-20260601-001"
title: "Old Meeting"
meeting_date: "2026-06-01"
---

# Old Meeting
""",
        encoding="utf-8",
    )

    new_data_dir = tmp_path / "25_Meetings" / "MTG-20260602-001" / "_data"
    new_data_dir.mkdir(parents=True)
    new_data = new_data_dir / "gpt_minutes.json"
    new_data.write_text(
        json.dumps({"meeting_id": "MTG-20260602-001", "title": "New Meeting", "meeting_date": "2026-06-02"}),
        encoding="utf-8",
    )
    os.utime(old_main, (1, 1))
    os.utime(new_data, (2, 2))

    meetings = meeting_workflow_app.discover_meetings(tmp_path)

    assert [item["meeting_id"] for item in meetings] == ["MTG-20260602-001", "MTG-20260601-001"]
    assert meetings[0]["title"] == "New Meeting"
    assert meeting_workflow_app.suggest_meeting_id(meetings) == "MTG-20260602-001"
    assert meeting_workflow_app.choose_initial_meeting_id("", meetings) == "MTG-20260602-001"
    assert meeting_workflow_app.choose_initial_meeting_id("missing", meetings) == "MTG-20260602-001"
    assert meeting_workflow_app.choose_initial_meeting_id("MTG-20260601-001", meetings) == "MTG-20260601-001"


def test_discover_meetings_from_source_notes(tmp_path: Path) -> None:
    import meeting_workflow_app

    source_dir = tmp_path / "20_Sources"
    source_dir.mkdir(parents=True)
    (source_dir / "MTG-20260602-001_source.md").write_text(
        """---
type: source
meeting_id: "MTG-20260602-001"
title: "Source Meeting"
meeting_date: "2026-06-02"
main_note: "25_Meetings/MTG-20260602-001/MTG-20260602-001.md"
---

# Source Meeting
""",
        encoding="utf-8",
    )

    meetings = meeting_workflow_app.discover_meetings(tmp_path)

    assert meetings[0]["meeting_id"] == "MTG-20260602-001"
    assert meetings[0]["title"] == "Source Meeting"
    assert meetings[0]["meeting_date"] == "2026-06-02"


def test_korean_action_text_translates_common_script_messages() -> None:
    import meeting_workflow_app

    assert "would create" not in meeting_workflow_app.korean_action_text("would create C:/x.md")
    assert "unchanged" not in meeting_workflow_app.korean_action_text("unchanged C:/x.md")


def test_selected_existing_file_rejects_empty_and_directory(tmp_path: Path) -> None:
    import meeting_workflow_app

    try:
        meeting_workflow_app.selected_existing_file("", "missing")
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected empty file selection to fail")

    try:
        meeting_workflow_app.selected_existing_file(str(tmp_path), "missing")
    except ValueError as exc:
        assert str(tmp_path) in str(exc)
    else:
        raise AssertionError("Expected directory selection to fail")

    file_path = tmp_path / "gpt.md"
    file_path.write_text("{}", encoding="utf-8")
    assert meeting_workflow_app.selected_existing_file(str(file_path), "missing") == file_path


def test_meeting_id_in_path_detects_source_id() -> None:
    import meeting_workflow_app

    path = "C:/x/20_Sources/00_Originals/MTG-20260601-001/transcript/stt.txt"
    assert meeting_workflow_app.meeting_id_in_path(path) == "MTG-20260601-001"
    assert meeting_workflow_app.meeting_id_in_path("C:/x/stt.txt") == ""


def test_state_round_trip(tmp_path: Path) -> None:
    state = WorkflowState(
        root=str(tmp_path),
        meeting_id="MTG-20260601-001",
        title="Demo Meeting",
        meeting_date="2026-06-01",
        source_file="C:/sample/source.m4a",
        gpt_input_file="C:/sample/input.md",
        gpt_output_file="C:/sample/output.md",
        copy_raw=True,
    )
    state.save(tmp_path)
    loaded = WorkflowState.load(tmp_path)
    assert loaded.meeting_id == "MTG-20260601-001"
    assert loaded.copy_raw is True
    assert loaded.gpt_input_file.endswith("input.md")
    assert loaded.gpt_output_file.endswith("output.md")


def test_launcher_manual_gpt_flow_labels_are_ordered() -> None:
    import meeting_workflow_app

    labels = [
        meeting_workflow_app.TXT["new_meeting"],
        meeting_workflow_app.TXT["register_source"],
        meeting_workflow_app.TXT["generate_gpt_input"],
        meeting_workflow_app.TXT["open_gpt_input"],
        meeting_workflow_app.TXT["select_gpt_output"],
        meeting_workflow_app.TXT["preview_import"],
        meeting_workflow_app.TXT["apply_import"],
        meeting_workflow_app.TXT["open_review"],
        meeting_workflow_app.TXT["refresh_dashboard"],
        meeting_workflow_app.TXT["run_validation"],
    ]

    assert labels == [
        "새 회의 만들기",
        "원본/STT 등록",
        "GPT 입력 파일 생성",
        "GPT 입력 파일 열기",
        "GPT 결과 파일 선택",
        "가져오기 미리보기",
        "가져오기 적용",
        "Review 열기",
        "Dashboard 갱신",
        "Validation 실행",
    ]


def test_replace_generated_block_preserves_manual_content() -> None:
    original = """# Note

Manual before.

<!-- AUTO-GENERATED: SUMMARY START -->
old
<!-- AUTO-GENERATED: SUMMARY END -->

Manual after.
"""
    updated = replace_generated_block(original, "SUMMARY", "new")
    assert "Manual before." in updated
    assert "Manual after." in updated
    assert "old" not in updated
    assert "new" in updated
