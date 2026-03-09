```instructions
---
applyTo: "**/*.py,**/*.md,**/*.json"
---

# Project Documentation — Instructions for Copilot

## When to execute

After CHANGE_DOC, whenever architecture, modules, or system behaviour change.

## Target file

`PROJECT_DOC.md` in `Documentation/`.
Update relevant sections in-place. Create the file if it does not exist.

## Document structure

```markdown
# Project Documentation — AliExpress-SteuerGrabber

**Last updated:** YYYY-MM-DD

## 1. Project Overview
<Purpose: download AliExpress invoice PDFs and generate a categorized summary table with EUR conversion for German tax declarations.>

## 2. How It Works
<Login flow, order scraping, invoice download, categorization, exchange rate lookup, CSV export.>

## 3. Key Modules

| Module / File | Responsibility |
|---|---|
| `grabber.py` | Main entry point — orchestrates the full workflow |

## 4. Configuration
<.env file, environment variables, dependencies.>

## 5. Output
<invoices/ directory, orders_summary.csv, console table.>

## 6. Known Limitations / Open Issues
<Current issues, workarounds.>

## 7. Revision History
| Date | Summary |
|---|---|
| YYYY-MM-DD | Initial documentation |
```

## Rules

- **MUST** update "Last updated" date on every edit.
- **MUST** update Key Modules when files are added/removed.
- **SHOULD** keep descriptions concise — prefer tables and bullet lists.
```
