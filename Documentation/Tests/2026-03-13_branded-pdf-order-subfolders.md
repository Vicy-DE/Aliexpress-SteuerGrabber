# Test Report — Branded PDF with Order Subfolders

**Date:** 2026-03-13
**Python version:** 3.14.3
**Script tested:** `utils/downloader.py`, `utils/pdf_generator.py`, `utils/md_generator.py`, `utils/receipt.py`, `utils/reports.py`, `grabber.py`

---

## Summary

| Metric | Value |
|---|---|
| Tests executed | 100 |
| Tests passed | 100 |
| Tests failed | 0 |
| Execution time | ~0.9s |

## Full Script Run

| Metric | Value |
|---|---|
| Total orders | 1074 |
| PDF invoices | 1074 (100%) |
| MD invoices | 1074 (100%) |
| Detail page screenshots | 1074 (100%) |
| Receipt page HTMLs | 681 (63%) |
| Product images downloaded | 17 |
| Failed downloads | 0 |
| Screenshot fallbacks | 0 |

## Verified Features

| Feature | Status | Notes |
|---|---|---|
| Order subfolders | ✓ | `invoices/<year>/<order_id>/` with 1074 folders |
| Resources subfolder | ✓ | `resources/` in every order folder |
| Detail page screenshot | ✓ | `detail_page.png` in all 1074 orders |
| Receipt HTML capture | ✓ | `receipt_page.html` in 681 orders (tax-ui available) |
| Product image download | ✓ | 17 images downloaded via HTTP to resources/ |
| AliExpress branded header | ✓ | Orange banner (232,65,24) with white text on PDF |
| EUR price on PDF | ✓ | USD + EUR with exchange rate and date |
| Octopart on PDF | ✓ | Component Identification section for electronics |
| Octopart on MD | ✓ | Table with Part/Info/Octopart columns |
| Polished MD format | ✓ | Tables, dividers, blockquotes, footer |

## Test Coverage

### Existing Tests (unchanged, all pass)
- Categorization: 17 tests (electronics, automotive, other, edge cases)
- Date parsing: 11 tests (multiple formats)
- Receipt extraction: 3 tests
- MD generation: 3 tests (basic, electronics, without receipt data)
- PNG-to-PDF: 3 tests (basic, missing file, with order data)
- Part extraction: 4 tests (ESP32, PCF8574, ATmega, WS2812, none)
- Part lookup: 6 tests (exact, case-insensitive, prefix, unknown, diode, sensor)
- OCR: 15 tests (text extraction, price extraction, MD verification, image comparison)

### Backward Compatibility
- All 100 existing tests pass without modification
- New `convert_png_to_pdf()` kwargs (`ecb_rates`, `product_images`, `receipt_data`) are optional with `None` defaults
- New `_add_text_page()` kwargs are optional — existing behavior preserved when not provided

## How to reproduce

```powershell
py -3 -m pytest tests/ -v
```
