# Prompt 03: Review Check

Review the draft extraction for uncertainty.

Important constraints:

- This is a manual ChatGPT workflow. Do not mention API execution or API keys.
- Speaker labels and role labels are unreliable unless independently confirmed in the source.
- Flag every missing, ambiguous, or inferred owner, decider, and due date.
- Do not resolve uncertainty by guessing.
- Keep the fixed section names used by the repository importer.

Return Markdown using these exact headings. Put review findings in `### 검토 필요 항목`.

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
