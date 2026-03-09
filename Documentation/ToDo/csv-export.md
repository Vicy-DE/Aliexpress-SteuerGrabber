# Todo: CSV Export & Summary Table

**Created:** 2026-03-09
**Requirement:** [Req #6 — CSV Export & Summary Table](../Requirements/requirements.md)
**Status:** Done

---

## Tasks

- [x] Build summary rows with all columns
  - [x] Order ID, Date, Items (truncated 80 chars), Category
  - [x] Price (USD), Rate (USD/EUR), Rate Date, Price (EUR)
- [x] Print formatted table to console using `tabulate` (grid format)
- [x] Print summary totals (Electronics EUR, Other EUR, Grand total EUR)
- [x] Export to `orders_summary.csv` with semicolon delimiter
  - [x] Use `csv.DictWriter` with UTF-8 encoding
- [x] Handle empty order list gracefully
- [x] Script runs without errors
- [x] CHANGE_LOG.md updated

---

## Notes

- Semicolon delimiter chosen for Excel compatibility in German locale (comma is the decimal separator).
