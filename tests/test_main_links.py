from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from import_gpt_minutes import import_gpt_minutes
from register_source import register_source
from render_meeting_repo import validate_repo


def copy_template(root: Path) -> None:
    target = root / "90_Templates" / "meeting_main_template.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text((ROOT / "90_Templates" / "meeting_main_template.md").read_text(encoding="utf-8"), encoding="utf-8")


def build_valid_sample(root: Path) -> None:
    copy_template(root)
    register_source(root, "MTG-20260601-001", "Demo", "2026-06-01", apply=True)
    payload = {
        "meeting_id": "MTG-20260601-001",
        "summary": ["Summary"],
        "decisions": [{"id": "D-001", "title": "Decision", "decider": "A", "owner": "B", "due": "2026-06-10"}],
        "actions": [{"id": "A-001", "task": "Action", "owner": "B", "due": "2026-06-10"}],
        "issues": [{"id": "I-001", "issue": "Issue", "owner": "B"}],
    }
    gpt_file = root / "gpt.json"
    gpt_file.write_text(json.dumps(payload), encoding="utf-8")
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
