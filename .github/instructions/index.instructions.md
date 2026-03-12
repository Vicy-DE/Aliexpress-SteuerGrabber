```instructions
---
applyTo: "**/*.py,**/*.ps1,**/*.sh,**/*.md,**/*.json,**/*.csv"
---

# AliExpress-SteuerGrabber — Copilot Instructions

## After Every Code Change — MANDATORY

1. **Test** → run `py -3 -m pytest tests/ -v` — fix failures before continuing. [TEST_DOC](documentation/TEST_DOC.instructions.md)
2. **Document** → append `Documentation/CHANGE_LOG.md` + update `Documentation/PROJECT_DOC.md`. [CHANGE_DOC](documentation/CHANGE_DOC.instructions.md) · [PROJECT_DOC](documentation/PROJECT_DOC.instructions.md)
3. **Test Report** → save test results to `Documentation/Tests/<YYYY-MM-DD>_<feature>.md`. [TEST_DOC](documentation/TEST_DOC.instructions.md)
4. **Commit** → stage relevant files, write Conventional Commit message — **never push**. [COMMIT](documentation/COMMIT.instructions.md)

## Before New Features

1. Update `Documentation/Requirements/requirements.md` → [REQUIREMENTS_DOC](documentation/REQUIREMENTS_DOC.instructions.md)
2. Create `Documentation/ToDo/<feature>.md` → [TODO_DOC](documentation/TODO_DOC.instructions.md)

## Rules

- Scripts: [SCRIPTS](CODING/SCRIPTS.instructions.md)
- Coding: [COMMENTS](CODING/COMMENTS.instructions.md)
- All Python scripts use `snake_case` naming.
- Use script-relative paths — never `os.getcwd()`.
- Sensitive data (cookies, tokens) must NEVER be committed — use `.env` files excluded via `.gitignore`.
- Prices are stored in the original currency (USD) AND converted to EUR using the historical exchange rate of the order date, rounded **up** to the next full cent.
- PDF invoices are saved to `invoices/<year>/` with the naming pattern `<yyyy-mm-dd>-<order_id>.pdf`.
- Each PDF has a companion Markdown invoice file `<yyyy-mm-dd>-<order_id>.md`.
- Yearly summaries are saved to `analysis/<year>_summary.md`.
- Electronics invoices are copied to `analysis/electronics/`.
- The summary table is exported as `orders_summary.csv` and `orders_summary.md`.
```
