# Prompt 01: Main Meeting Minutes

You are helping prepare meeting minutes from user-provided source text.

Important constraints:

- This is a manual ChatGPT workflow. Do not mention API calls, API keys, automation, or code clients.
- Treat transcript speaker names and roles as unreliable unless the source explicitly confirms them.
- Do not infer owners, deciders, or due dates from unclear speaker labels.
- If owner, decider, or due date is missing or inferred, mark it as review-required.
- Preserve uncertainty. Use `Unknown` instead of guessing.

Input fields:

- Meeting ID: `{{meeting_id}}`
- Meeting title: `{{title}}`
- Meeting date: `{{meeting_date}}`

Task:

1. Produce concise meeting minutes.
2. Separate facts from interpretation.
3. List likely decisions, actions, and issues, but mark uncertain ownership or authority.
4. Include short source references or quote fragments where useful.

Return Markdown with these headings:

```markdown
## Summary
## Decisions
## Actions
## Issues
## Open Questions
```

