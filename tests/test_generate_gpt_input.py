from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_gpt_input import GPT_OUTPUT_PLACEHOLDER, generate_gpt_input, gpt_input_path, gpt_output_path
from register_source import register_source


def copy_template(root: Path) -> None:
    target = root / "90_Templates" / "meeting_main_template.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text((ROOT / "90_Templates" / "meeting_main_template.md").read_text(encoding="utf-8"), encoding="utf-8")


def write_archived_stt(root: Path) -> Path:
    stt_file = root / "20_Sources" / "00_Originals" / "sample_stt.txt"
    stt_file.parent.mkdir(parents=True, exist_ok=True)
    stt_file.write_text("화자 1: 일정은 아직 확인이 필요합니다.\n화자 2: 담당자는 추후 확인합니다.\n", encoding="utf-8")
    return stt_file


def register_sample_meeting(root: Path, stt_file: Path) -> None:
    copy_template(root)
    register_source(
        root=root,
        meeting_id="MTG-20260601-001",
        title="Demo Meeting",
        meeting_date="2026-06-01",
        source_file=stt_file,
        apply=True,
    )


def test_generate_gpt_input_defaults_to_dry_run(tmp_path: Path) -> None:
    stt_file = write_archived_stt(tmp_path)
    register_sample_meeting(tmp_path, stt_file)

    actions = generate_gpt_input(
        root=tmp_path,
        meeting_id="MTG-20260601-001",
        source_file=stt_file,
        apply=False,
    )

    assert any("would create" in action for action in actions)
    assert not gpt_input_path(tmp_path, "MTG-20260601-001").exists()
    assert not gpt_output_path(tmp_path, "MTG-20260601-001").exists()


def test_generate_gpt_input_writes_prompt_and_reserves_output(tmp_path: Path) -> None:
    stt_file = write_archived_stt(tmp_path)
    register_sample_meeting(tmp_path, stt_file)

    generate_gpt_input(
        root=tmp_path,
        meeting_id="MTG-20260601-001",
        source_file=stt_file,
        apply=True,
    )

    input_text = gpt_input_path(tmp_path, "MTG-20260601-001").read_text(encoding="utf-8")
    assert "# GPT 입력 파일 - MTG-20260601-001" in input_text
    assert "speaker_reliable: false" in input_text
    assert "role_reliable: false" in input_text
    assert "raw_archive: 20_Sources/00_Originals/sample_stt.txt" in input_text
    assert "stt_file: 20_Sources/00_Originals/sample_stt.txt" in input_text
    assert "### Decision 후보" in input_text
    assert "### Action 후보" in input_text
    assert "### Open Issue 후보" in input_text
    assert "화자 1: 일정은 아직 확인이 필요합니다." in input_text

    output_path = gpt_output_path(tmp_path, "MTG-20260601-001")
    assert output_path.read_text(encoding="utf-8").strip() == GPT_OUTPUT_PLACEHOLDER

    output_path.write_text("manual ChatGPT result\n", encoding="utf-8")
    actions = generate_gpt_input(
        root=tmp_path,
        meeting_id="MTG-20260601-001",
        source_file=stt_file,
        apply=True,
    )
    assert output_path.read_text(encoding="utf-8") == "manual ChatGPT result\n"
    assert any("unchanged existing GPT output file" in action for action in actions)


def test_generate_gpt_input_requires_registered_meeting(tmp_path: Path) -> None:
    stt_file = write_archived_stt(tmp_path)

    try:
        generate_gpt_input(
            root=tmp_path,
            meeting_id="MTG-20260601-001",
            source_file=stt_file,
            apply=False,
        )
    except FileNotFoundError as exc:
        assert "Register raw/STT first" in str(exc)
    else:
        raise AssertionError("Expected GPT input generation before registration to fail")


def test_generate_gpt_input_rejects_empty_cleaned_stt(tmp_path: Path) -> None:
    stt_file = tmp_path / "20_Sources" / "00_Originals" / "empty_stt.txt"
    stt_file.parent.mkdir(parents=True, exist_ok=True)
    stt_file.write_text("   \n", encoding="utf-8")
    register_sample_meeting(tmp_path, stt_file)

    try:
        generate_gpt_input(
            root=tmp_path,
            meeting_id="MTG-20260601-001",
            source_file=stt_file,
            apply=False,
        )
    except ValueError as exc:
        assert "empty after cleaning" in str(exc)
    else:
        raise AssertionError("Expected empty STT to fail")


def test_generate_gpt_input_rejects_source_path_meeting_id_mismatch(tmp_path: Path) -> None:
    copy_template(tmp_path)
    stt_file = tmp_path / "20_Sources" / "00_Originals" / "MTG-20260602-001_stt.txt"
    stt_file.parent.mkdir(parents=True, exist_ok=True)
    stt_file.write_text("synthetic STT", encoding="utf-8")

    try:
        register_source(
            root=tmp_path,
            meeting_id="MTG-20260601-001",
            title="Demo",
            meeting_date="2026-06-01",
            source_file=stt_file,
            apply=True,
        )
    except ValueError as exc:
        assert "different meeting_id" in str(exc)
    else:
        raise AssertionError("Expected mismatched source/STT path to fail")


def test_generate_gpt_input_decodes_utf16_stt(tmp_path: Path) -> None:
    stt_file = tmp_path / "20_Sources" / "00_Originals" / "utf16_stt.txt"
    stt_file.parent.mkdir(parents=True, exist_ok=True)
    stt_file.write_text("발화자 1 (00:00)\n로직 검토 일정을 논의했다.\n", encoding="utf-16")
    register_sample_meeting(tmp_path, stt_file)

    generate_gpt_input(
        root=tmp_path,
        meeting_id="MTG-20260601-001",
        source_file=stt_file,
        apply=True,
    )

    input_text = gpt_input_path(tmp_path, "MTG-20260601-001").read_text(encoding="utf-8")
    assert "발화자 1 (00:00)" in input_text
    assert "로직 검토 일정을 논의했다." in input_text
    assert "\ufffd" not in input_text


def test_generate_gpt_input_rejects_corrupt_stt_decode(tmp_path: Path) -> None:
    stt_file = tmp_path / "20_Sources" / "00_Originals" / "corrupt_stt.txt"
    stt_file.parent.mkdir(parents=True, exist_ok=True)
    stt_file.write_bytes(b"\xff\xff\xff")
    register_sample_meeting(tmp_path, stt_file)

    try:
        generate_gpt_input(
            root=tmp_path,
            meeting_id="MTG-20260601-001",
            source_file=stt_file,
            apply=False,
        )
    except ValueError as exc:
        assert "could not be decoded cleanly" in str(exc)
    else:
        raise AssertionError("Expected corrupt STT decoding to fail")


def test_generate_gpt_input_prefers_registered_archive_over_stale_source_file(tmp_path: Path) -> None:
    archived_stt = tmp_path / "20_Sources" / "00_Originals" / "archived_stt.txt"
    archived_stt.parent.mkdir(parents=True, exist_ok=True)
    archived_stt.write_text("ARCHIVE STT TEXT", encoding="utf-8")
    stale_source = tmp_path / "stale_external_source.txt"
    stale_source.write_text("STALE SOURCE TEXT", encoding="utf-8")
    register_sample_meeting(tmp_path, archived_stt)

    generate_gpt_input(
        root=tmp_path,
        meeting_id="MTG-20260601-001",
        source_file=stale_source,
        apply=True,
    )

    input_text = gpt_input_path(tmp_path, "MTG-20260601-001").read_text(encoding="utf-8")
    assert "stt_file: 20_Sources/00_Originals/archived_stt.txt" in input_text
    assert "ARCHIVE STT TEXT" in input_text
    assert "STALE SOURCE TEXT" not in input_text
