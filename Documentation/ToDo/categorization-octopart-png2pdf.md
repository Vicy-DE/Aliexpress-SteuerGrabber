# Todo: Categorization Fix, Octopart Part Extraction, PNG→PDF Conversion

**Created:** 2026-03-12
**Requirement:** [Req #5 — Order Categorization](../Requirements/requirements.md), [Req #3 — Invoice PDF Download](../Requirements/requirements.md)
**Status:** Done

---

## Tasks

- [x] Remove broad "cnc" from ELECTRONICS_KEYWORDS, replace with specific terms
- [x] Add AUTOMOTIVE_KEYWORDS exclusion list (~40 keywords)
- [x] Rewrite `categorize_order()` to check automotive exclusions first
- [x] Add `extract_part_numbers()` with 40+ regex patterns for component identification
- [x] Rewrite `generate_octopart_report()` with extracted part numbers in table format
- [x] Update `generate_invoice_md()` — "Component Identification" section with part numbers
- [x] Add `convert_png_to_pdf()` using fpdf2 + PIL
- [x] Update `download_invoice_from_detail_page()` — screenshot fallback converts PNG→PDF
- [x] Add batch PNG→PDF conversion step in `main()`
- [x] Fix `extract_receipt_data()` — direct tax-ui URL instead of iframe detection
- [x] Script runs without errors
- [x] Tests pass (`py -3 -m pytest tests/ -v`) — 78 passed
- [x] CHANGE_LOG.md updated
- [x] Full rerun: 1071/1071 PDFs, 0 screenshots, 0 failures

---

## Notes

- Octopart API (Nexar GraphQL) requires OAuth2 authentication — not available without token. Website blocks automated access with CAPTCHA. Part numbers are extracted locally via regex patterns.
- Headed mode (`headless=False`) required for reliable receipt extraction in Playwright Firefox.
- `MAX_WORKERS` reduced from 4 to 2 to avoid resource contention with headed browsers.
