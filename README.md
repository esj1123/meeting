# MEETING

MEETING is the software source repo for the 09_Meeting manual GPT workflow.

The program does not call the OpenAI API, does not require API keys, and does not include `openai_client.py`. ChatGPT is used manually by the user outside this program.

## Workflow

1. Create or select a meeting.
2. Register raw/STT files.
3. Generate `40_Work/<meeting_id>_gpt_input.md`.
4. Copy the GPT input into ChatGPT manually.
5. Save the ChatGPT response as `40_Work/<meeting_id>_gpt_output.md`.
6. Preview the import.
7. Apply the import.
8. Render Main / Decision / Action / Issue notes.
9. Update dashboards.
10. Run the quality gate.

## Source And Artifact Roles

- GitHub MEETING repo: software source, templates, scripts, tests, and generated Markdown notes.
- Google Drive folder: operational/export target for generated artifacts after review and quality gate.
- Raw/STT source files controlled by this repo must live under `20_Sources/00_Originals/`.

## Commands

```powershell
py scripts\register_source.py --title "Demo Meeting" --date 2026-06-01 --apply
py scripts\generate_gpt_input.py --meeting-id MTG-20260601-001 --apply
py scripts\import_gpt_minutes.py --meeting-id MTG-20260601-001 --gpt-output 40_Work\MTG-20260601-001_gpt_output.md
py scripts\import_gpt_minutes.py --meeting-id MTG-20260601-001 --gpt-output 40_Work\MTG-20260601-001_gpt_output.md --apply
py scripts\render_meeting_repo.py --apply
py scripts\update_dashboards.py --apply
py scripts\quality_gate.py --root .
```

All file-changing scripts default to dry-run unless `--apply` is provided. Import preview records workflow state so apply can verify that the same GPT output was reviewed before writing generated notes.

## Dashboard Targets

- `00_Dashboard/Meeting_HOME.md`
- `00_Dashboard/Action_Queue.md`
- `00_Dashboard/Decision_Register.md`

## Speaker Uncertainty

Galaxy STT speaker and role labels are unreliable by default. Owners, deciders, and due dates must be explicit in source text; otherwise items remain review-required.

Action notes remain compatible with the current convention:

```yaml
type: issue
issue_subtype: action
tags:
  - workflow/action
```
