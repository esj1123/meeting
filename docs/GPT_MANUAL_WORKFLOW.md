# Manual GPT Meeting Workflow

This repository uses ChatGPT manually. The program does not call the OpenAI API, does not require API keys, and does not include an `openai_client.py` module.

## Repository Flow

1. Register the meeting source with `scripts/register_source.py` or the GUI launcher.
2. Copy prompt 01 from `90_Templates/prompts/gpt_prompt_01_main_minutes.md` into ChatGPT with the meeting source text.
3. Copy prompt 02 into ChatGPT to extract decisions, actions, and issues as JSON.
4. Copy prompt 03 into ChatGPT for a review check.
5. Save the pasted GPT result to a local Markdown or JSON file.
6. Import the pasted output with `scripts/import_gpt_minutes.py`.
7. Render notes and dashboards with `scripts/render_meeting_repo.py` and `scripts/update_dashboards.py`.
8. Run validation with `scripts/render_meeting_repo.py --validate`.

All file-changing scripts default to dry run. Add `--apply` only after reviewing the planned changes.

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
