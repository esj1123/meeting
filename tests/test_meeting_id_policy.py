from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from meeting_workflow_state import (
    derived_item_id,
    next_meeting_id,
    parse_frontmatter,
    registry_action,
    source_meeting_date,
    validate_derived_id,
    validate_meeting_id,
)
from register_source import register_source


def copy_template(root: Path) -> None:
    target = root / "90_Templates" / "meeting_main_template.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text((ROOT / "90_Templates" / "meeting_main_template.md").read_text(encoding="utf-8"), encoding="utf-8")


def test_meeting_id_validation() -> None:
    assert validate_meeting_id("MTG-20260602-001")
    assert not validate_meeting_id("2026-06-02-demo")
    assert not validate_meeting_id("MTG-20260602-1")


def test_next_meeting_id_scans_existing_notes_and_registry(tmp_path: Path) -> None:
    meeting_dir = tmp_path / "25_Meetings" / "MTG-20260602-001"
    meeting_dir.mkdir(parents=True)
    (meeting_dir / "MTG-20260602-001.md").write_text(
        """---
type: knowledge
meeting_id: "MTG-20260602-001"
meeting_date: "2026-06-02"
---
""",
        encoding="utf-8",
    )
    registry_action(tmp_path, "MTG-20260602-002", "Voided Meeting", "2026-06-02", apply=True)

    assert next_meeting_id(tmp_path, "2026-06-02") == "MTG-20260602-003"
    assert next_meeting_id(tmp_path, "2026-06-03") == "MTG-20260603-001"


def test_source_meeting_date_extracts_source_filename_date() -> None:
    assert source_meeting_date(Path("recording_260601_150105.txt")) == "2026-06-01"
    assert source_meeting_date(Path("meeting_2026-06-01.txt")) == "2026-06-01"
    assert source_meeting_date(Path("audio_150105.txt")) == ""


def test_register_source_empty_id_uses_source_filename_date(tmp_path: Path) -> None:
    copy_template(tmp_path)
    archive_dir = tmp_path / "20_Sources" / "00_Originals"
    archive_dir.mkdir(parents=True)
    source_file = archive_dir / "recording_260601_150105.txt"
    source_file.write_text("synthetic STT", encoding="utf-8")

    register_source(
        tmp_path,
        "",
        "Source Date Meeting",
        "2026-06-03",
        source_file=source_file,
        apply=True,
    )

    main_note = tmp_path / "25_Meetings" / "MTG-20260601-001" / "MTG-20260601-001.md"
    frontmatter = parse_frontmatter(main_note.read_text(encoding="utf-8"))
    assert frontmatter["meeting_id"] == "MTG-20260601-001"
    assert frontmatter["meeting_date"] == "2026-06-01"


def test_derived_item_ids() -> None:
    assert derived_item_id("decision", "MTG-20260602-001", 1) == "DEC-20260602-001-001"
    assert derived_item_id("action", "MTG-20260602-001", 2) == "ACT-20260602-001-002"
    assert derived_item_id("issue", "MTG-20260602-001", 3) == "ISS-20260602-001-003"
    assert validate_derived_id("RUN-20260602-001-001")


def test_register_source_rejects_reused_registry_id_without_existing_files(tmp_path: Path) -> None:
    copy_template(tmp_path)
    registry_action(tmp_path, "MTG-20260602-001", "Voided Meeting", "2026-06-02", apply=True)

    try:
        register_source(tmp_path, "MTG-20260602-001", "Reuse", "2026-06-02", apply=False)
    except ValueError as exc:
        assert "cannot be reused" in str(exc)
    else:
        raise AssertionError("Expected registry reuse to be rejected")
