# Todo: Invoice PDF Download

**Created:** 2026-03-09
**Requirement:** [Req #3 — Invoice PDF Download](../Requirements/requirements.md)
**Status:** Done

---

## Tasks

- [x] Create `invoices/` directory if it does not exist
- [x] Skip download if `<order_id>.pdf` already exists
- [x] Navigate to order detail page
- [x] Search for invoice/receipt download button (multiple selectors)
- [x] Handle download via Playwright `expect_download`
- [x] Fall back to `page.pdf()` for page-as-PDF
- [x] Handle errors gracefully (print warning, continue with next order)
- [x] Add polite delay between requests (1s)
- [x] Script runs without errors
- [x] CHANGE_LOG.md updated

---

## Notes

- `page.pdf()` only works in headless Chromium — in headed Firefox mode it may fail, so the warning is expected.
- Invoice button selectors may need updating as AliExpress changes their UI.
