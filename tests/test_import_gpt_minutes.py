from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from import_gpt_minutes import import_gpt_minutes
from register_source import register_source


def copy_template(root: Path) -> None:
    target = root / "90_Templates" / "meeting_main_template.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text((ROOT / "90_Templates" / "meeting_main_template.md").read_text(encoding="utf-8"), encoding="utf-8")


def test_import_json_creates_links_and_review_flags(tmp_path: Path) -> None:
    copy_template(tmp_path)
    register_source(
        root=tmp_path,
        meeting_id="MTG-20260601-001",
        title="Demo Meeting",
        meeting_date="2026-06-01",
        apply=True,
    )
    payload = {
        "meeting_id": "MTG-20260601-001",
        "title": "Demo Meeting",
        "meeting_date": "2026-06-01",
        "summary": ["Reviewed launch readiness."],
        "decisions": [
            {
                "id": "D-001",
                "title": "Use the manual GPT workflow.",
                "decider": "Unknown",
                "owner": "Unknown",
                "due": "Unknown",
                "review_required": False,
            }
        ],
        "actions": [
            {"id": "A-001", "task": "Confirm owner.", "owner": "Unknown", "due": "Unknown"}
        ],
        "issues": [
            {"id": "I-001", "issue": "Speaker attribution is uncertain.", "owner": "Unknown"}
        ],
    }
    gpt_file = tmp_path / "gpt_output.md"
    gpt_file.write_text("```json\n" + json.dumps(payload) + "\n```\n", encoding="utf-8")
    actions = import_gpt_minutes(tmp_path, "MTG-20260601-001", gpt_output=gpt_file, apply=True)
    assert any("gpt_minutes.json" in action for action in actions)
    main = tmp_path / "25_Meetings" / "MTG-20260601-001" / "MTG-20260601-001.md"
    main_text = main.read_text(encoding="utf-8")
    assert "decisions/DEC-20260601-001-001.md" in main_text
    assert "actions/ACT-20260601-001-001.md" in main_text
    assert "issues/ISS-20260601-001-001.md" in main_text
    data = json.loads((tmp_path / "25_Meetings" / "MTG-20260601-001" / "_data" / "gpt_minutes.json").read_text(encoding="utf-8"))
    assert data["decisions"][0]["review_required"] is True
    assert data["actions"][0]["review_required"] is True


def test_reimport_preserves_manual_content(tmp_path: Path) -> None:
    copy_template(tmp_path)
    register_source(tmp_path, "MTG-20260601-001", "Demo", "2026-06-01", apply=True)
    payload = {"meeting_id": "MTG-20260601-001", "summary": ["First"], "decisions": [], "actions": [], "issues": []}
    gpt_file = tmp_path / "gpt.json"
    gpt_file.write_text(json.dumps(payload), encoding="utf-8")
    import_gpt_minutes(tmp_path, "MTG-20260601-001", gpt_output=gpt_file, apply=True)
    main = tmp_path / "25_Meetings" / "MTG-20260601-001" / "MTG-20260601-001.md"
    text = main.read_text(encoding="utf-8").replace("Add user-authored notes here.", "Manual owner note.")
    main.write_text(text, encoding="utf-8")
    payload["summary"] = ["Second"]
    gpt_file.write_text(json.dumps(payload), encoding="utf-8")
    import_gpt_minutes(tmp_path, "MTG-20260601-001", gpt_output=gpt_file, apply=True)
    updated = main.read_text(encoding="utf-8")
    assert "Manual owner note." in updated
    assert "Second" in updated
    assert "First" not in updated


def test_import_rejects_directory_as_gpt_output(tmp_path: Path) -> None:
    try:
        import_gpt_minutes(tmp_path, "MTG-20260601-001", gpt_output=tmp_path, apply=False)
    except ValueError as exc:
        assert "must be a file" in str(exc)
    else:
        raise AssertionError("Expected directory GPT output to fail")
