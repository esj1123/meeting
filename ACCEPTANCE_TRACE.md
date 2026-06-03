# Acceptance Trace

This trace covers the manual no-API GPT workflow merge blockers found in the pre-merge review.

| Review item | Patch coverage | Verification |
|---|---|---|
| Quality gate entrypoint | `scripts/quality_gate.py` runs scoped validation and no-API checks. | `py scripts/quality_gate.py --root .` |
| Dashboard targets | `scripts/update_dashboards.py` writes `00_Dashboard/Meeting_HOME.md`, `Action_Queue.md`, and `Decision_Register.md`. | `tests/test_quality_gate_and_dashboards.py` |
| GPT output preconditions | `scripts/import_gpt_minutes.py` rejects empty, `.`, directory, missing, non-`.md`, wrong filename/path, empty content, and missing fixed sections. | `tests/test_import_gpt_minutes.py` |
| Preview before apply | Import preview records `.workflow/<meeting_id>_import_preview.json`; apply requires the same file hash. | `tests/test_import_gpt_minutes.py` |
| Meeting ID mismatch guard | Core source/STT/audio/GPT path validation rejects conflicting `MTG-YYYYMMDD-NNN` values. | `tests/test_generate_gpt_input.py`, `tests/test_import_gpt_minutes.py` |
| Empty STT rejection | GPT input generation fails if cleaned STT text is empty. | `tests/test_generate_gpt_input.py` |
| Preview counts and warnings | Import returns main/decision/action/open issue/review counts and missing owner/due/decider warnings. | `tests/test_import_gpt_minutes.py` |
| Fixed prompt sections | Prompt templates use `### Main Meeting Note`, `### Decision 후보`, `### Action 후보`, `### Open Issue 후보`, and `### 검토 필요 항목`. | `tests/test_manual_gpt_workflow.py` |
| README and workflow docs | `README.md`, `docs/GPT_MANUAL_WORKFLOW.md`, and `docs/RUNBOOK.md` document source/artifact roles, manual ChatGPT use, dashboards, and quality gate. | Direct review |
| No API automation | No `openai_client.py`, API keys, or OpenAI API client calls are added. | `tests/test_manual_gpt_workflow.py`, `scripts/quality_gate.py` |

Action items remain `type: issue` with `issue_subtype: action` and `workflow/action`.
