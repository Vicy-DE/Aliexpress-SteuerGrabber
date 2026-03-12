# Test Report — Automotive Category, Local Part Database, PNG-to-PDF Copyable Text

**Date:** 2026-03-12
**Python version:** 3.14.3
**Script tested:** `grabber.py`

---

## Summary

| Result | Count |
|---|---|
| PASS | 85 |
| FAIL | 0 |

---

## Test Cases

### TC-01 — Automotive categorization returns "Automotive"

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion`
**Input / stimulus:** Automotive items (motorcycle, OBD, diagnostic tools)
**Expected result:** `categorize_order()` returns "Automotive"
**Actual result:** PASS — All 8 automotive tests return "Automotive", 3 pure electronics tests still return "Electronics"

### TC-02 — lookup_part exact match

**Script:** `tests/test_grabber.py::TestLookupPart::test_exact_match`
**Input / stimulus:** Part number "ESP32"
**Expected result:** Returns dict with manufacturer "Espressif"
**Actual result:** PASS

### TC-03 — lookup_part prefix match

**Script:** `tests/test_grabber.py::TestLookupPart::test_prefix_match`
**Input / stimulus:** Part number "STM32F407VET6" (extends known "STM32F407")
**Expected result:** Returns dict with manufacturer "STMicroelectronics"
**Actual result:** PASS

### TC-04 — lookup_part unknown part

**Script:** `tests/test_grabber.py::TestLookupPart::test_unknown_part`
**Input / stimulus:** Part number "XYZZY9999"
**Expected result:** Returns None
**Actual result:** PASS

### TC-05 — convert_png_to_pdf with order data

**Script:** `tests/test_grabber.py::TestConvertPngToPdf::test_creates_pdf_with_order_data`
**Input / stimulus:** PNG image + order dict with items and total
**Expected result:** PDF created with text page + screenshot page, size > 500 bytes
**Actual result:** PASS

### TC-06 — Octopart report uses local database

**Script:** `tests/test_grabber.py::TestGenerateOctopartReport::test_contains_part_info`
**Input / stimulus:** Electronics orders with ESP32
**Expected result:** Report contains "Espressif" manufacturer from local database
**Actual result:** PASS

### TC-07 — Markdown invoice uses component identification

**Script:** `tests/test_grabber.py::TestGenerateInvoiceMd::test_electronics_md_has_component_identification`
**Input / stimulus:** ESP32 electronics order
**Expected result:** Markdown contains "Component Identification" section with "Espressif"
**Actual result:** PASS

---

## Full Rerun Verification

| Metric | Result |
|---|---|
| Total orders | 1071 |
| PDF invoices | 1070 (99.9%) |
| Screenshot fallbacks | 0 |
| Failed downloads | 1 |
| 2023 invoices | 106 PDFs, 0 screenshots (100%) |
| 2024 invoices | 226 PDFs, 0 screenshots (100%) |
| 2025 invoices | 169 PDFs, 0 screenshots (100%) |
| 2026 invoices | 61 PDFs, 0 screenshots (100%) |
| Electronics orders | 256 |
| Automotive orders | 280 |
| Other orders | 535 |
