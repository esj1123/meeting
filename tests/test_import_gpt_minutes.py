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


def test_import_fixed_manual_gpt_output_sections(tmp_path: Path) -> None:
    copy_template(tmp_path)
    register_source(tmp_path, "MTG-20260601-001", "Demo", "2026-06-01", apply=True)
    gpt_output = tmp_path / "gpt_output.md"
    gpt_output.write_text(
        """### Main Meeting Note
- 출시 전 점검 항목을 검토했다.

### Decision 후보
| ID | 제목 | 결정 내용 | 근거 | 확인 필요 |
|---|---|---|---|---|
| D-1 | 배포 방식 | 확정 표현이 없어 결정 후보로만 남김 | "결정은 다음 회의에서" | 확인 필요 |

### Action 후보
| ID | 할 일 | 담당자 | 기한 | 근거 | 확인 필요 |
|---|---|---|---|---|---|
| A-1 | 일정 재확인 | 확인 필요 | 미정 | "추후 확인" | 확인 필요 |

### Open Issue 후보
| ID | 이슈 | 확인 주체 | 근거 | 다음 조치 |
|---|---|---|---|---|
| I-1 | 담당자 불명확 | PM | "담당자는 추후 확인" | 다음 회의에서 확인 |

### 검토 필요 항목
| 위치 | 검토 사유 | 확인할 내용 |
|---|---|---|
| Action A-1 | 담당자와 기한 불명확 | 실제 담당자와 기한 |
""",
        encoding="utf-8",
    )

    import_gpt_minutes(tmp_path, "MTG-20260601-001", gpt_output=gpt_output, apply=True)

    data = json.loads((tmp_path / "25_Meetings" / "MTG-20260601-001" / "_data" / "gpt_minutes.json").read_text(encoding="utf-8"))
    assert data["title"] == "Demo"
    assert data["summary"] == ["출시 전 점검 항목을 검토했다."]
    assert data["decisions"][0]["id"] == "DEC-20260601-001-001"
    assert data["actions"][0]["task"] == "일정 재확인"
    assert data["actions"][0]["owner"] == "Unknown"
    assert data["actions"][0]["due"] == "Unknown"
    assert data["actions"][0]["review_required"] is True
    assert data["issues"][0]["issue"] == "담당자 불명확"

    action_note = tmp_path / "25_Meetings" / "MTG-20260601-001" / "actions" / "ACT-20260601-001-001.md"
    action_text = action_note.read_text(encoding="utf-8")
    assert "type: issue" in action_text
    assert "issue_subtype: action" in action_text
    assert "workflow/action" in action_text


def test_import_rejects_raw_stt_as_gpt_output(tmp_path: Path) -> None:
    try:
        import_gpt_minutes(
            tmp_path,
            "MTG-20260601-001",
            gpt_text="화자 1: 원본 STT입니다.\n화자 2: 아직 ChatGPT 결과가 아닙니다.",
            apply=False,
        )
    except ValueError as exc:
        assert "raw/STT source file" in str(exc)
    else:
        raise AssertionError("Expected raw STT import to fail")
