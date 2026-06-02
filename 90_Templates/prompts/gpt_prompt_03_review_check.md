# Prompt 03: Review Check

Review the draft meeting extraction for uncertainty.

Important constraints:

- This is a manual ChatGPT workflow. Do not mention API execution or API keys.
- Speaker labels and role labels are unreliable unless independently confirmed in the source.
- Flag every missing, ambiguous, or inferred owner, decider, and due date.
- Do not resolve uncertainty by guessing.

Return Markdown with these headings:

```markdown
## Blocking Review Items
## Owner Checks
## Decider Checks
## Due Date Checks
## Source Evidence Gaps
```

For each item, include the affected item ID and the reason review is required.

