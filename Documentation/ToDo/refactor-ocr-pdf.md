# Todo: Refactor, OCR PDF Creation, Image Comparison

**Created:** 2026-03-12
**Requirement:** [Req #10–14](../Requirements/requirements.md)
**Status:** Complete

---

## Tasks

### Refactoring (Req #10)
- [x] Create `utils/` package with `__init__.py`
- [x] Extract `utils/config.py` (constants, keywords, PART_DATABASE)
- [x] Extract `utils/exchange.py` (ECB rates, USD→EUR)
- [x] Extract `utils/categorizer.py` (categorize_order, extract_part_numbers, lookup_part)
- [x] Extract `utils/firefox.py` (find_firefox_profile, extract_firefox_cookies)
- [x] Extract `utils/scraper.py` (scrape_order_list, scrape_orders_via_api, parse functions)
- [x] Extract `utils/receipt.py` (extract_receipt_data)
- [x] Extract `utils/pdf_generator.py` (generate_invoice_pdf, convert_png_to_pdf)
- [x] Extract `utils/md_generator.py` (generate_invoice_md)
- [x] Extract `utils/reports.py` (summaries, CSV export, run report, octopart)
- [x] Extract `utils/downloader.py` (download, enrich, batch processing)
- [x] Reduce `grabber.py` to main() orchestration only
- [x] Verify no file exceeds 500 lines

### Receipt Fix (Req #11)
- [x] Ensure receipt screenshots match `orginal/` reference format
- [x] Verify ≥90% of 2023-2025 orders produce text PDFs

### 2017 Price Fix (Req #12)
- [x] Add OCR-based price extraction for old orders without tax-ui data

### OCR PDF Pipeline (Req #13)
- [x] Build PDF from screenshot image (not from MD)
- [x] Extract text from screenshot via Tesseract OCR
- [x] Compare OCR text against MD content for validation

### Image-PDF Testing (Req #14)
- [x] Convert PDF back to image
- [x] Compare against original screenshot at quarter resolution (≥99% similar)
- [x] Extract text from PDF-image via OCR and compare with MD

### Standard
- [x] Script runs without errors
- [x] Tests pass (`py -3 -m pytest tests/ -v`) — 100 passed
- [x] CHANGE_LOG.md updated
- [x] requirements.md updated (if scope changed)

---

## Notes

- Tesseract installed at: C:\Users\Layer\AppData\Local\Programs\Tesseract-OCR
- Dependencies added: pytesseract, opencv-python, numpy
- Original reference screenshots in `orginal/` folder (8 files)
