```instructions
---
applyTo: "**/*.py,**/*.md,**/*.json"
---

# Change Documentation — Instructions for Copilot

## When to execute

After every verified code change.

## Target file

`CHANGE_LOG.md` in `Documentation/`.
Append a new entry at the top (newest first). Create the file if it does not exist.

## Entry format

```markdown
## [YYYY-MM-DD] <Short title>

### What was changed
- <file or component> — <brief description>

### Why it was changed
<Reason>

### What it does / expected behaviour
<Description of the new or corrected behaviour>

### Verified
- Run: OK / FAIL
```

## Rules

- **MUST** create an entry for every change session.
- **MUST** list every modified file with a one-line summary.
- **MUST** state a clear reason (the "why").
- **MUST NOT** omit the entry even for "small" changes.
```
