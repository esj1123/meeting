# Prompt 02: Extract Decisions, Actions, And Issues

Convert the meeting minutes into the JSON schema below.

Important constraints:

- This is a manual ChatGPT workflow. Do not call any API and do not require an API key.
- Speaker and role labels are unreliable by default.
- Do not invent owners, deciders, or due dates.
- If an owner, decider, or due date is missing, ambiguous, or inferred, set `review_required` to `true`.
- Use `Unknown` for unknown owner, decider, or due.
- Use derived IDs when possible: `DEC-YYYYMMDD-MMM-NNN`, `ACT-YYYYMMDD-MMM-NNN`, and `ISS-YYYYMMDD-MMM-NNN`.
- If you cannot derive the ID confidently, keep a temporary local ID; the repository importer will normalize it.

Return only one fenced JSON block:

```json
{
  "meeting_id": "{{meeting_id}}",
  "title": "{{title}}",
  "meeting_date": "{{meeting_date}}",
  "summary": [
    "Concise factual summary item."
  ],
  "decisions": [
    {
      "id": "DEC-YYYYMMDD-MMM-001",
      "title": "Decision title",
      "decider": "Unknown",
      "owner": "Unknown",
      "due": "Unknown",
      "review_required": true,
      "source_refs": ["Short evidence fragment or timestamp"]
    }
  ],
  "actions": [
    {
      "id": "ACT-YYYYMMDD-MMM-001",
      "task": "Action task",
      "owner": "Unknown",
      "due": "Unknown",
      "review_required": true,
      "source_refs": ["Short evidence fragment or timestamp"]
    }
  ],
  "issues": [
    {
      "id": "ISS-YYYYMMDD-MMM-001",
      "issue": "Issue text",
      "owner": "Unknown",
      "review_required": true,
      "source_refs": ["Short evidence fragment or timestamp"]
    }
  ],
  "review": {
    "review_required": true,
    "reasons": ["owner_decider_due_uncertainty"]
  }
}
```
