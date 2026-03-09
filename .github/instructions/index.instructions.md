```instructions
---
applyTo: "**/*.py,**/*.ps1,**/*.sh,**/*.md,**/*.json,**/*.csv"
---

# AliExpress-SteuerGrabber — Copilot Instructions

## After Every Code Change — MANDATORY

1. **Test** → run the script in dry-run or test mode to verify no regressions.
2. **Document** → append `Documentation/CHANGE_LOG.md` + update `Documentation/PROJECT_DOC.md`. [CHANGE_DOC](documentation/CHANGE_DOC.instructions.md) · [PROJECT_DOC](documentation/PROJECT_DOC.instructions.md)
3. **Commit** → stage relevant files, write Conventional Commit message — **never push**. [COMMIT](documentation/COMMIT.instructions.md)

## Rules

- Scripts: [SCRIPTS](CODING/SCRIPTS.instructions.md)
- Coding: [COMMENTS](CODING/COMMENTS.instructions.md)
- All Python scripts use `snake_case` naming.
- Use script-relative paths — never `os.getcwd()`.
- Sensitive data (cookies, tokens) must NEVER be committed — use `.env` files excluded via `.gitignore`.
- Prices are stored in the original currency (USD) AND converted to EUR using the historical exchange rate of the order date, rounded **up** to the next full cent.
- PDF invoices are saved to `invoices/` with the naming pattern `<order_id>.pdf`.
- The summary table is exported as `orders_summary.csv` and printed to the console.
```
