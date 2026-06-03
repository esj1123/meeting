from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from register_source import register_source


def copy_template(root: Path) -> None:
    target = root / "90_Templates" / "meeting_main_template.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text((ROOT / "90_Templates" / "meeting_main_template.md").read_text(encoding="utf-8"), encoding="utf-8")


def test_register_source_defaults_to_dry_run(tmp_path: Path) -> None:
    copy_template(tmp_path)
    actions = register_source(
        root=tmp_path,
        meeting_id="",
        title="Demo Meeting",
        meeting_date="2026-06-01",
        apply=False,
    )
    assert any("would create" in action for action in actions)
    assert not (tmp_path / "25_Meetings").exists()
    assert not (tmp_path / "20_Sources").exists()


def test_no_openai_client_module_exists() -> None:
    assert not (ROOT / "openai_client.py").exists()
    assert not (ROOT / "scripts" / "openai_client.py").exists()


def test_register_source_does_not_overwrite_existing_source_note(tmp_path: Path) -> None:
    copy_template(tmp_path)
    register_source(
        root=tmp_path,
        meeting_id="MTG-20260601-001",
        title="Demo",
        meeting_date="2026-06-01",
        apply=True,
    )
    source_note = tmp_path / "20_Sources" / "MTG-20260601-001_source.md"
    original = source_note.read_text(encoding="utf-8") + "\nManual source note.\n"
    source_note.write_text(original, encoding="utf-8")
    register_source(
        root=tmp_path,
        meeting_id="MTG-20260601-001",
        title="Changed",
        meeting_date="2026-06-02",
        apply=True,
    )
    assert source_note.read_text(encoding="utf-8") == original


def test_register_source_rejects_directory_source(tmp_path: Path) -> None:
    copy_template(tmp_path)
    try:
        register_source(
            root=tmp_path,
            meeting_id="MTG-20260601-001",
            title="Demo",
            meeting_date="2026-06-01",
            source_file=tmp_path,
            apply=False,
        )
    except ValueError as exc:
        assert "must be a file" in str(exc)
    else:
        raise AssertionError("Expected directory source file to fail")


def test_prompt_templates_are_manual_workflow_only() -> None:
    prompt_dir = ROOT / "90_Templates" / "prompts"
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in prompt_dir.glob("*.md"))
    assert "manual chatgpt workflow" in text
    assert "api key" in text
    assert "openai_client.py" not in text
    assert "### main meeting note" in text
    assert "### decision 후보" in text
    assert "### action 후보" in text
    assert "### open issue 후보" in text
    assert "### 검토 필요 항목" in text
