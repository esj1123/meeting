# Manual GPT Meeting Workflow

This repository uses ChatGPT manually. The program does not call the OpenAI API, does not require API keys, and does not include an `openai_client.py` module.

## Repository Flow

1. Register the meeting source with `scripts/register_source.py` or the GUI launcher.
2. Generate `40_Work/<meeting_id>_gpt_input.md` with `scripts/generate_gpt_input.py` or the GUI button `GPT 입력 파일 생성`.
3. Open the generated GPT input file, copy it into ChatGPT manually, and do not use API automation.
4. Save the ChatGPT response to `40_Work/<meeting_id>_gpt_output.md` or select another saved GPT output file.
5. Preview the pasted output import with `scripts/import_gpt_minutes.py`.
6. Apply the import after reviewing the preview.
7. Render notes and dashboards with `scripts/render_meeting_repo.py` and `scripts/update_dashboards.py`.
8. Run validation with `scripts/render_meeting_repo.py --validate`.

All file-changing scripts default to dry run. Add `--apply` only after reviewing the planned changes.

## Generated GPT Input

The generator creates the input file and reserves the expected output file:

```powershell
py scripts\generate_gpt_input.py --meeting-id MTG-20260601-001
py scripts\generate_gpt_input.py --meeting-id MTG-20260601-001 --apply
```

The GPT input includes meeting metadata, source/raw/STT references, `speaker_reliable: false`, `role_reliable: false`, uncertainty rules, the fixed manual output sections, and the STT text. The output placeholder contains only:

```markdown
<!-- Paste ChatGPT output below this line. Do not paste raw STT here. -->
```

The generator does not create fake GPT results and does not overwrite an existing GPT output file.

## Source Policy

Raw source files controlled by this repository belong only under:

`20_Sources/00_Originals/`

The launcher and CLI will not move or copy a raw file by default. The GUI exposes an explicit raw-copy confirmation, and the CLI requires both `--copy-raw` and `--confirm-copy` before a copy can happen with `--apply`.

If a source file remains outside the repository, the source note records it as an external reference. If a source file is already inside this repository but outside `20_Sources/00_Originals/`, registration fails instead of normalizing it silently.

## Main Records

Main meeting records live under:

`25_Meetings/<meeting_id>/<meeting_id>.md`

Meeting IDs use `MTG-YYYYMMDD-NNN`, for example `MTG-20260602-001`.

The main note is linked from the source note. The main note links to generated decision, action, and issue notes. User-authored content outside `AUTO-GENERATED` blocks must be preserved by render and import scripts.

## Generated Blocks

Generated content uses paired markers:

```markdown
<!-- AUTO-GENERATED: SUMMARY START -->
...
<!-- AUTO-GENERATED: SUMMARY END -->
```

Scripts replace only the named generated block. Manual notes, corrections, and context outside those blocks stay untouched.

## Speaker And Role Reliability

Speaker labels and roles are not trusted by default. The main note template sets:

```yaml
speaker_reliable: false
role_reliable: false
```

The GPT prompts ask ChatGPT to avoid converting uncertain speaker labels into facts. Owners, deciders, and due dates remain review-required when they are missing or inferred.
