# Meeting ID Policy

## Canonical Meeting ID

Use this immutable meeting ID format:

```text
MTG-YYYYMMDD-NNN
```

Example:

```text
MTG-20260602-001
MTG-20260602-002
MTG-20260603-001
```

Regex:

```regex
^MTG-\d{8}-\d{3}$
```

Rules:

- `YYYYMMDD` is the meeting start date.
- `NNN` is the daily sequence number.
- Do not include title, project, equipment, owner, speaker, or role in `meeting_id`.
- Store topic/project/equipment details in metadata such as `series_id`, `meeting_type`, `equipment_ref`, and `title`.
- Once created, `meeting_id` is immutable.
- Never reuse a meeting ID, even when a meeting is deleted or voided.

## Current Repository Paths

The current 09_Meeting structure keeps main meeting notes under:

```text
25_Meetings/<meeting_id>/<meeting_id>.md
```

Source notes are generated under:

```text
20_Sources/<meeting_id>_source.md
```

Raw files controlled by this repository remain allowed only under:

```text
20_Sources/00_Originals/
```

## Registry

Used IDs are recorded in:

```text
40_Work/meeting_id_registry.jsonl
```

Each line is JSON:

```json
{"meeting_id":"MTG-20260602-001","meeting_date":"2026-06-02","title":"Example","status":"active"}
```

The registry is used with existing notes to calculate the next daily sequence number.

## Derived IDs

Decision, action, and issue IDs derive from the parent meeting ID:

```text
DEC-YYYYMMDD-MMM-NNN
ACT-YYYYMMDD-MMM-NNN
ISS-YYYYMMDD-MMM-NNN
RUN-YYYYMMDD-MMM-NNN
```

Example for `MTG-20260602-001`:

```text
DEC-20260602-001-001
ACT-20260602-001-001
ISS-20260602-001-001
RUN-20260602-001-001
```

Action notes remain `type: issue` plus action workflow metadata until an `action_item` type is formally added.

## GUI Behavior

The GUI proposes a meeting ID before creation:

1. Use the selected meeting date.
2. Scan existing meeting notes, source notes, and `meeting_id_registry.jsonl`.
3. Find existing `MTG-YYYYMMDD-*` IDs.
4. Propose the next sequence number.

Manual override is accepted only when it matches the canonical regex.

