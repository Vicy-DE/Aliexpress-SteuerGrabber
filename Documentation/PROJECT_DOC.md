# Project Documentation — AliExpress-SteuerGrabber

**Last updated:** 2026-03-09

## 1. Project Overview

Download all AliExpress invoice PDFs and generate a categorized summary table with EUR conversion for German tax declarations (Steuererklärung).

## 2. How It Works

1. **Login** — Opens Chromium via Playwright; on first run the user logs in manually. Session state is persisted for future runs.
2. **Order Scraping** — First attempts API interception from network responses, falls back to DOM scraping. Paginates automatically.
3. **Data Enrichment** — Visits each order detail page to fill missing fields (items, price, date).
4. **Invoice Download** — Clicks the invoice/receipt button; if unavailable, saves the detail page as PDF.
5. **Exchange Rate** — Fetches ECB historical USD/EUR daily rates (cached for 24h). Finds the rate for the order date (or nearest previous business day).
6. **Categorization** — Matches item titles against a keyword list to classify as "Electronics" or "Other".
7. **Output** — Prints a formatted table to the console and exports `orders_summary.csv`.

## 3. Key Modules

| Module / File | Responsibility |
|---|---|
| `grabber.py` | Main entry point — orchestrates login, scraping, downloading, categorization, and export |

## 4. Configuration

| Item | Description |
|---|---|
| `.env` | AliExpress email and password (optional, used for reference only — login is manual) |
| `requirements.txt` | Python dependencies: playwright, python-dotenv, requests, tabulate |
| `browser_data/` | Playwright persistent browser profile (auto-created) |
| `browser_state.json` | Saved cookie/storage state |
| `ecb_rates_cache.json` | Cached ECB exchange rates (auto-refreshed every 24h) |

## 5. Output

| Path | Description |
|---|---|
| `invoices/<order_id>.pdf` | Individual invoice PDFs per order |
| `orders_summary.csv` | Categorized table: Order ID, Date, Items, Category, USD price, EUR rate, EUR price |

## 6. Known Limitations / Open Issues

- AliExpress frequently changes their DOM structure; selectors may need updating.
- ECB rates cover the last ~90 days via the daily feed; for older orders, the most recent available rate is used as a fallback.
- PDF download via the invoice button may not work for all orders; the fallback saves the detail page as PDF (headless Chromium only).
- Currency detection assumes USD; orders in other currencies may need manual adjustment.

## 7. Revision History

| Date | Summary |
|---|---|
| 2026-03-09 | Initial project setup with invoice grabber, EUR conversion, and categorization |
