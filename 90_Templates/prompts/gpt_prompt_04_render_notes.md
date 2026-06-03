# Prompt 04: Render Notes

Prepare clean Markdown wording for the meeting repository.

Important constraints:

- This is a manual ChatGPT workflow. Do not create API automation.
- Preserve `확인 필요` values for uncertain owner, decider, or due fields.
- Keep uncertain items review-required.
- Do not rely on speaker or role labels as facts.
- Keep the fixed section names used by the repository importer.

Return concise Markdown using these exact headings:

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
