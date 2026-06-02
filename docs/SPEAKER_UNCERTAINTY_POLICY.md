# Speaker Uncertainty Policy

Speaker names and roles from transcripts are unreliable unless independently confirmed.

## Defaults

Main meeting notes must default to:

```yaml
speaker_reliable: false
role_reliable: false
```

These flags mean:

- Speaker labels may be diarization guesses, transcript artifacts, initials, or role placeholders.
- Role labels may be inferred from context and must not be treated as authoritative.
- Owners, deciders, and due dates derived from speaker labels require review.

## Owner, Decider, And Due Rules

Use `review_required: true` when:

- An action owner is missing, unclear, or inferred from a speaker label.
- A decision decider is missing, unclear, or inferred from a speaker label.
- A due date is missing, ambiguous, relative, or inferred.
- A role is used as a proxy for a person.

Use explicit values only when the source text states them clearly.

## Acceptable Unknowns

Prefer honest uncertainty over invented structure:

```yaml
owner: Unknown
decider: Unknown
due: Unknown
review_required: true
```

Do not convert `Speaker 1`, `PM`, `lead`, or `team` into a named owner unless the source explicitly supports that conversion.

