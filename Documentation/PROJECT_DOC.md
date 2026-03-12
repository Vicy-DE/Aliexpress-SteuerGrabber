# Project Documentation — AliExpress-SteuerGrabber

**Last updated:** 2026-03-13

## 1. Project Overview

Download all AliExpress invoice PDFs and generate a categorized summary table with EUR conversion for German tax declarations (Steuererklärung).

## 2. How It Works

1. **Login** — Extracts session cookies from the user's running Firefox browser (copies `cookies.sqlite` to avoid lock conflicts).
2. **Order Scraping** — Injects cookies into Playwright Firefox. Scrapes order list from DOM with automatic pagination via "View orders" button.
3. **Parallel Processing** — Splits orders across 2 headed browser instances (`MAX_WORKERS=2`). Each worker navigates to order detail pages and extracts receipt data.
4. **Receipt Extraction** — Navigates directly to the tax-ui URL (`https://www.aliexpress.com/p/tax-ui/index.html?isGrayMatch=true&orderId={order_id}`) and scrapes order ID, items, prices, VAT, shipping address via CSS selectors. Falls back to screenshot + PNG→PDF conversion with a copyable text page (order details) followed by the screenshot image if extraction fails.
5. **PDF & MD Generation** — Generates PDF invoices with copyable text (fpdf2) and companion Markdown files. Organized into year-based subfolders: `invoices/<year>/<date>-<order_id>.pdf`.
6. **Exchange Rate** — Fetches ECB historical USD/EUR daily rates (cached for 24h). Uses the rate for the order date (or nearest previous business day). Rounds up to next cent.
7. **Categorization** — Three categories: **Electronics**, **Automotive**, **Other**. Checks automotive keywords first (motorcycle, OBD, HEX V2, carburetor, diagnostic, etc.) — items matching automotive keywords are classified as "Automotive" regardless of electronics keywords. Remaining items are matched against electronics keywords using word-boundary regex.
8. **Component Identification** — Extracts electronic part numbers (ESP32, STM32, ATmega, 1N4007, etc.) from item titles using 40+ regex patterns. Looks up identified parts in a local **PART_DATABASE** (~80 curated entries) to show manufacturer and description in MD invoice files and a consolidated report.
9. **Output** — Prints formatted summary table, exports CSV, generates yearly summaries, and copies electronics invoices to a dedicated folder.

## 3. Key Modules

| Module / File | Responsibility |
|---|---|
| `grabber.py` | Thin main entry point (181 lines) — orchestrates login, parallel scraping, and report generation |
| `utils/config.py` | Constants, paths, URLs, keywords, PART_DATABASE, PART_NUMBER_PATTERNS, TESSERACT_CMD |
| `utils/exchange.py` | ECB rate fetching and USD→EUR conversion |
| `utils/categorizer.py` | Order classification (Electronics/Automotive/Other), part extraction, part lookup |
| `utils/firefox.py` | Firefox profile detection and cookie extraction |
| `utils/scraper.py` | Order list scraping, API interception, date/price parsing |
| `utils/receipt.py` | Tax-ui receipt data extraction via browser JS |
| `utils/pdf_generator.py` | PDF generation, OCR text/price extraction, image-PDF comparison |
| `utils/md_generator.py` | Per-order Markdown invoice generation |
| `utils/reports.py` | Summary tables, CSV export, yearly summaries, Octopart report |
| `utils/downloader.py` | Invoice download, order enrichment, parallel batch processing |
| `tests/test_grabber.py` | Unit tests — 85 tests for core logic (categorization, parsing, generation) |
| `tests/test_ocr_pdf.py` | OCR and image-PDF comparison tests — 15 tests |

## 4. Configuration

| Item | Description |
|---|---|
| `.env` | Optional — AliExpress email/password for reference |
| `requirements.txt` | Python dependencies: playwright, python-dotenv, requests, tabulate, fpdf2, Pillow, pytest, pytesseract, opencv-python |
| `ecb_rates_cache.json` | Cached ECB exchange rates (auto-refreshed every 24h) |
| `MAX_WORKERS` | Number of parallel browser instances (default: 2, headed mode) |

## 5. Output

| Path | Description |
|---|---|
| `invoices/<year>/<date>-<order_id>.pdf` | Individual PDF invoices with copyable text |
| `invoices/<year>/<date>-<order_id>.md` | Companion Markdown invoices with component identification (manufacturer + description from local database, for electronics) |
| `analysis/<year>_summary.md` | Yearly summary with totals by category |
| `analysis/electronics/` | Copies of electronics order invoices |
| `analysis/octopart_search.md` | Consolidated part identification with extracted part numbers, manufacturers, and descriptions from local database |
| `orders_summary.csv` | Categorized table: Order ID, Date, Items, Category, USD price, EUR rate, EUR price |
| `orders_summary.md` | Overall order summary in Markdown format |

## 6. Documentation Structure

| Path | Purpose |
|---|---|
| `Documentation/Requirements/requirements.md` | Feature requirements with traceability matrix |
| `Documentation/ToDo/<feature>.md` | Todo checklists per feature (implementation history) |
| `Documentation/Tests/<date>_<feature>.md` | Test reports |
| `Documentation/CHANGE_LOG.md` | Change log (newest first) |
| `Documentation/PROJECT_DOC.md` | This file |

## 7. Known Limitations / Open Issues

- AliExpress frequently changes their DOM structure; selectors may need updating.
- ECB rates cover the last ~90 days via the daily feed; for older orders, the most recent available rate is used as a fallback.
- Currency detection assumes USD; orders in other currencies may need manual adjustment.
- Octopart API requires Nexar OAuth2 authentication; a curated local PART_DATABASE (~80 entries) is used instead of live API queries.
- Headed mode (`headless=False`) is required for reliable receipt extraction; headless mode breaks the tax-ui page.
- Tesseract OCR must be installed separately (`winget install UB-Mannheim.TesseractOCR` on Windows). OCR text quality depends on screenshot resolution and font rendering.

## 8. Revision History

| Date | Summary |
|---|---|
| 2026-03-13 | Refactor to multi-module architecture (max 500 LOC/file), OCR pipeline, image-PDF comparison |
| 2026-03-12 | Automotive category, local part database, copyable-text fallback PDFs, direct receipt URL |
| 2026-03-12 | Automotive exclusion, part number extraction, PNG→PDF conversion, direct receipt URL |
| 2026-03-09 | Add complete documentation framework, tests, and requirements |
| 2026-03-09 | Initial project setup with invoice grabber, EUR conversion, and categorization |
