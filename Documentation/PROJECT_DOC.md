# Project Documentation — AliExpress-SteuerGrabber

**Last updated:** 2026-03-12

## 1. Project Overview

Download all AliExpress invoice PDFs and generate a categorized summary table with EUR conversion for German tax declarations (Steuererklärung).

## 2. How It Works

1. **Login** — Extracts session cookies from the user's running Firefox browser (copies `cookies.sqlite` to avoid lock conflicts).
2. **Order Scraping** — Injects cookies into Playwright Firefox. Scrapes order list from DOM with automatic pagination via "View orders" button.
3. **Parallel Processing** — Splits orders across 2 headed browser instances (`MAX_WORKERS=2`). Each worker navigates to order detail pages and extracts receipt data.
4. **Receipt Extraction** — Navigates directly to the tax-ui URL (`https://www.aliexpress.com/p/tax-ui/index.html?isGrayMatch=true&orderId={order_id}`) and scrapes order ID, items, prices, VAT, shipping address via CSS selectors. Falls back to screenshot + PNG→PDF conversion if extraction fails.
5. **PDF & MD Generation** — Generates PDF invoices with copyable text (fpdf2) and companion Markdown files. Organized into year-based subfolders: `invoices/<year>/<date>-<order_id>.pdf`.
6. **Exchange Rate** — Fetches ECB historical USD/EUR daily rates (cached for 24h). Uses the rate for the order date (or nearest previous business day). Rounds up to next cent.
7. **Categorization** — Matches item titles against electronics keywords using word-boundary regex. Checks automotive exclusion keywords first (motorcycle, OBD, HEX V2, carburetor, etc.) — items matching both automotive and electronics keywords are classified as "Other".
8. **Component Identification** — Extracts electronic part numbers (ESP32, STM32, ATmega, 1N4007, etc.) from item titles using 40+ regex patterns. Generates Octopart search links for identified parts in MD invoice files and a consolidated report.
9. **Output** — Prints formatted summary table, exports CSV, generates yearly summaries, and copies electronics invoices to a dedicated folder.

## 3. Key Modules

| Module / File | Responsibility |
|---|---|
| `grabber.py` | Main entry point — orchestrates login, parallel scraping, receipt extraction, PDF/MD generation, categorization, Octopart search, and export |
| `tests/test_grabber.py` | Unit tests — EUR conversion, date parsing, categorization, automotive exclusion, part number extraction, order parsing, PDF/MD generation, PNG→PDF conversion, Octopart report (78 tests) |

## 4. Configuration

| Item | Description |
|---|---|
| `.env` | Optional — AliExpress email/password for reference |
| `requirements.txt` | Python dependencies: playwright, python-dotenv, requests, tabulate, fpdf2, Pillow, pytest |
| `ecb_rates_cache.json` | Cached ECB exchange rates (auto-refreshed every 24h) |
| `MAX_WORKERS` | Number of parallel browser instances (default: 2, headed mode) |

## 5. Output

| Path | Description |
|---|---|
| `invoices/<year>/<date>-<order_id>.pdf` | Individual PDF invoices with copyable text |
| `invoices/<year>/<date>-<order_id>.md` | Companion Markdown invoices with Octopart links (for electronics) |
| `analysis/<year>_summary.md` | Yearly summary with totals by category |
| `analysis/electronics/` | Copies of electronics order invoices |
| `analysis/octopart_search.md` | Consolidated part identification with extracted part numbers and Octopart search links |
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
- Octopart API requires Nexar OAuth2 authentication; part numbers are extracted locally via regex patterns instead of live API queries.
- Headed mode (`headless=False`) is required for reliable receipt extraction; headless mode breaks the tax-ui page.

## 8. Revision History

| Date | Summary |
|---|---|
| 2026-03-12 | Automotive exclusion, part number extraction, PNG→PDF conversion, direct receipt URL |
| 2026-03-09 | Add complete documentation framework, tests, and requirements |
| 2026-03-09 | Initial project setup with invoice grabber, EUR conversion, and categorization |
