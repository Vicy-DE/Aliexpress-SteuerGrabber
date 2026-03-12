```instructions
---
applyTo: "**/*.py,**/*.md,**/*.json"
---

# Requirements Documentation — Instructions for Copilot

## When to execute

**On every feature request — before writing any code.**
Whenever the user asks to add, change, or remove a feature, update `Documentation/Requirements/requirements.md` first, then proceed with implementation.

## Target file

`Documentation/Requirements/requirements.md`
Edit sections in-place. Create the file if it does not exist.

---

## Requirement entry format

Each feature is one top-level section numbered sequentially. Use the template below:

```markdown
## <N>. <Feature Name> — <Key Technology / Interface>

| Item | Detail |
|---|---|
| **Module / Component** | <grabber / categorizer / exchange / export> |
| **Interface** | <Browser automation / HTTP API / File I/O / N/A> |
| **Dependencies** | <playwright / requests / sqlite3 / etc.> |
| **Requirements** | <Detailed prose: what must be implemented, how it must behave, constraints.> |
```

---

## Traceability Matrix (end of file)

Keep the matrix at the end of the file. After adding or modifying a requirement:
1. Add a new row for every new requirement.
2. Update the "Depends On" column to list all requirement numbers this one depends on.
3. Remove rows for deleted requirements and re-check all dependency references.

```markdown
## Traceability Matrix

| Req # | Feature | Depends On |
|---|---|---|
| N | <Feature short name> | <Req #, … or —> |
```

---

## Rules

- **MUST** update `requirements.md` before starting any implementation work on a feature request.
- **MUST** assign the next available sequential requirement number.
- **MUST** fill every table row — do not leave items blank; write "N/A" when not applicable.
- **MUST** update the Traceability Matrix in the same edit that adds or changes a requirement.
- **MUST** mark obsolete requirements with `~~strikethrough~~` and append `*(removed YYYY-MM-DD)*` rather than deleting them.
- **MUST NOT** change existing requirement numbers — add new ones or mark old ones obsolete.
- **SHOULD** keep "Requirements" prose concise: prefer bullet lists inside the table cell.
```
