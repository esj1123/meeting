# Prompt 04: Render Notes

Prepare clean Markdown wording for the meeting repository.

Important constraints:

- This is a manual ChatGPT workflow. Do not create API automation.
- Preserve `Unknown` values for uncertain owner, decider, or due fields.
- Keep `review_required: true` on uncertain items.
- Do not rely on speaker or role labels as facts.

Return concise Markdown sections:

```markdown
## Summary
## Decisions
## Actions
## Issues
## Review Required
```

Use stable item IDs from the extracted JSON. Do not introduce new IDs unless an item lacks one.

