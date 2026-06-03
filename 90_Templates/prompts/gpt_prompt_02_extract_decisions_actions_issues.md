# Prompt 02: Extract Decisions, Actions, And Open Issues

Convert the meeting minutes into the fixed manual-import Markdown format below.

Important constraints:

- This is a manual ChatGPT workflow. Do not call any API and do not require an API key.
- Speaker and role labels from Galaxy STT are unreliable by default.
- Do not invent owners, deciders, or due dates.
- Use Decision only for confirmed decisions with clear source wording.
- If an owner, decider, or due date is missing, ambiguous, or inferred, write `확인 필요`.
- Put unresolved, unclear, or follow-up discussion items under `Open Issue 후보`.
- Keep the section names and table headers exactly as written.

```markdown
### Main Meeting Note

### Decision 후보
| ID | 제목 | 결정 내용 | 근거 | 확인 필요 |
|---|---|---|---|---|

### Action 후보
| ID | 할 일 | 담당자 | 기한 | 근거 | 확인 필요 |
|---|---|---|---|---|---|

### Open Issue 후보
| ID | 이슈 | 확인 주체 | 근거 | 다음 조치 |
|---|---|---|---|---|

### 검토 필요 항목
| 위치 | 검토 사유 | 확인할 내용 |
|---|---|---|
```
