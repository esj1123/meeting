# 09_Meeting Runbook

This runbook describes the no-API manual GPT workflow for meeting records.

## Start The Launcher

Run:

```powershell
.\START_MEETING_WORKFLOW.bat
```

The launcher uses `tkinter` and local Python only. It does not call a remote API.

## Register A Source

Dry run:

```powershell
py scripts\register_source.py --title "Demo Meeting" --date 2026-06-01
```

Apply:

```powershell
py scripts\register_source.py --title "Demo Meeting" --date 2026-06-01 --apply
```

To copy a raw file into the controlled archive, use the GUI confirmation path. The CLI also requires explicit flags:

```powershell
py scripts\register_source.py --title "Demo Meeting" --date 2026-06-01 --source-file C:\path\to\source.m4a --copy-raw --confirm-copy --apply
```

## Use ChatGPT Manually

After registering the source, generate the single manual GPT input file:

```powershell
py scripts\generate_gpt_input.py --meeting-id MTG-20260601-001
py scripts\generate_gpt_input.py --meeting-id MTG-20260601-001 --apply
```

This writes:

- `40_Work/MTG-20260601-001_gpt_input.md`
- `40_Work/MTG-20260601-001_gpt_output.md`

The output file is only a placeholder until the user saves the ChatGPT response there. Do not paste raw STT into the GPT output file.

The generated input file already includes the manual instructions, the uncertainty rules, the required output sections, and the STT text. Copy the input file into ChatGPT manually.

Save the pasted GPT output to the generated output path or another local Markdown/JSON file.

## Import GPT Output

Dry run:

```powershell
py scripts\import_gpt_minutes.py --meeting-id MTG-20260601-001 --gpt-output .\scratch\gpt_output.md
```

Apply:

```powershell
py scripts\import_gpt_minutes.py --meeting-id MTG-20260601-001 --gpt-output .\scratch\gpt_output.md --apply
```

The import updates generated blocks in the main note, creates or updates generated decision/action/issue notes, and stores normalized parsed data under the meeting folder.

## Render And Validate

Dry run render:

```powershell
py scripts\render_meeting_repo.py
```

Apply render:

```powershell
py scripts\render_meeting_repo.py --apply
```

Validate:

```powershell
py scripts\render_meeting_repo.py --validate
```

Update dashboards:

```powershell
py scripts\update_dashboards.py --apply
```

## Validation Coverage

Validation checks:

- Source notes link to existing main meeting notes.
- Main notes link to generated decision, action, and issue notes.
- Raw files inside the repository are stored only under `20_Sources/00_Originals/`.
- Missing or uncertain owner, decider, or due values are marked `review_required`.
- Generated block markers are paired correctly.

## Recovery

If an import result is wrong, edit only the pasted GPT output or the manual areas of notes, then rerun the import or render in dry-run mode. Do not hand-edit generated blocks unless you are intentionally overriding generated content and will not rerender it.
