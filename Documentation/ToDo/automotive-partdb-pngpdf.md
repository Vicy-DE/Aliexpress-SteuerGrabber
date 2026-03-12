# Todo: Automotive Category, Local Part Database, PNG-to-PDF Copyable Text

**Created:** 2025-07-27
**Requirement:** [Req #7 — Automotive Category](../Requirements/requirements.md), [Req #8 — Local Part Database](../Requirements/requirements.md), [Req #9 — PNG to PDF with Copyable Text](../Requirements/requirements.md)
**Status:** Done

---

## Tasks

- [x] `categorize_order()` returns "Automotive" for automotive keyword matches
- [x] Add `PART_DATABASE` with ~80 common electronic components
- [x] Add `lookup_part()` function for local part lookups
- [x] Rewrite `convert_png_to_pdf()` with text page from order data + screenshot page
- [x] Update `generate_invoice_md()` to use `lookup_part()` instead of Octopart links
- [x] Update `download_invoice_from_detail_page()` to pass `order` to `convert_png_to_pdf()`
- [x] Update `generate_octopart_report()` to use PART_DATABASE instead of search links
- [x] Update `generate_yearly_summary()` for 3 categories (Electronics, Automotive, Other)
- [x] Update `generate_order_summary()` for 3 categories
- [x] Update `main()` summary stats for 3 categories
- [x] Update batch PNG→PDF in `main()` to pass order data
- [x] Update tests for Automotive category, lookup_part, new report format
- [x] Script runs without errors
- [x] Tests pass (`py -3 -m pytest tests/ -v`) — 85 passed
- [x] CHANGE_LOG.md updated
- [x] requirements.md updated (Req #7, #8, #9 added)

---

## Notes

- 2023-2025 invoices already at 97-99% text PDF rate from receipt extraction.
- Remaining ~3% are old orders where tax-ui has no data.
- PNG→PDF now creates text page from scraped order data + screenshot as page 2.
- Octopart API requires OAuth2/API key — replaced with curated local database.
