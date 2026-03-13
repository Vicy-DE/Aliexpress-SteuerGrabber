# Test Report — Download Button Implementation

**Date:** 2026-03-13
**Feature:** Switch from screenshots to official AliExpress Download button

## Changes Tested

- `utils/receipt.py` — `download_receipt_image()` rewritten to use JavaScript interception
- `utils/downloader.py` — `download_invoice_from_detail_page()` uses download as primary method

## Test Execution

```
py -3 -m pytest tests/ -v
```

**Result:** 100 passed in 0.89s

## Full Run Verification

- **Total orders:** 1076
- **Downloaded via Download button:** 681 (2019–2026)
- **Screenshot fallback:** 395 (2017–2018, old orders without receipt content)
- **Errors:** 0
- **Output files:** 3228 (1076 PNG + 1076 PDF + 1076 MD)
- **Text-only PDFs:** 0 (all contain image content)

## Image Quality Comparison

| Metric | Reference (orginal/) | Output |
|---|---|---|
| Format | Downloaded receipt PNG | Downloaded receipt PNG |
| White pixel % | 93.3% | 98.0% |
| Browser chrome | None | None |
| Content match | — | Same receipt content |

All 8 reference orders found in output with matching content.
