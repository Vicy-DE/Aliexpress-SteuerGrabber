```instructions
---
applyTo: "**/*.py,**/*.md,**/*.json"
---

# Todo Documentation — Instructions for Copilot

## When to execute

**On every feature request — after updating `requirements.md`, before writing code.**
Also **after every implementation step** — tick completed items immediately.

## Target file

`Documentation/ToDo/<feature-name>.md`
The file is named after the feature using `kebab-case` (e.g., `invoice-download.md`, `eur-conversion.md`).
Create the file when the feature is first requested. Update it after every implementation step.

---

## File format

```markdown
# Todo: <Feature Name>

**Created:** YYYY-MM-DD
**Requirement:** [Req #N — <Feature Name>](../Requirements/requirements.md)
**Status:** In Progress / Done

---

## Tasks

- [ ] <Top-level task 1>
  - [ ] <Sub-task 1.1>
  - [ ] <Sub-task 1.2>
- [ ] <Top-level task 2>
- [ ] <Top-level task 3>
  - [ ] <Sub-task 3.1>
- [ ] Script runs without errors
- [ ] Tests pass (`py -3 -m pytest tests/ -v`)
- [ ] CHANGE_LOG.md updated
- [ ] requirements.md updated (if scope changed)

---

## Notes

<Optional: blockers, open questions, AliExpress quirks encountered, deferred items.>
```

---

## Naming convention

| Feature | File name |
|---|---|
| Firefox Cookie Extraction | `firefox-cookies.md` |
| Invoice Download | `invoice-download.md` |
| EUR Conversion | `eur-conversion.md` |
| Order Categorization | `order-categorization.md` |
| Order Scraping | `order-scraping.md` |
| CSV Export | `csv-export.md` |
| Any other feature | `<short-kebab-case-description>.md` |

---

## Rules

- **MUST** create the todo file when a feature is requested, immediately after updating `requirements.md`.
- **MUST** tick (`- [x]`) each task as soon as that implementation step is complete — do not batch-tick at the end.
- **MUST** include the final standard tasks (script runs, tests pass, CHANGE_LOG update) in every file.
- **MUST** update the `**Status:**` line to `Done` once all checkboxes are ticked.
- **MUST NOT** delete todo files when done — they serve as implementation history.
- **SHOULD** break each top-level task into sub-tasks when it involves more than one file or function.
```
