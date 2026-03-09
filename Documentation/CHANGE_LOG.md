## [2026-03-09] Initial project setup

### What was changed
- `grabber.py` — Main script: browser-based AliExpress order scraping, invoice PDF download, EUR conversion, categorization, CSV export
- `.github/instructions/` — Copilot instruction files adapted from RC-Servo project
- `requirements.txt` — Python dependencies (playwright, python-dotenv, requests, tabulate)
- `.env.example` — Template for credentials
- `.gitignore` — Exclude .env, invoices, caches, venv
- `README.md` — Setup and usage instructions
- `Documentation/PROJECT_DOC.md` — Project documentation

### Why it was changed
Initial creation of the AliExpress invoice grabber tool for German tax declarations.

### What it does / expected behaviour
- Opens a Chromium browser via Playwright for manual AliExpress login
- Scrapes all completed orders (API interception + DOM fallback)
- Downloads invoice PDFs to `invoices/` directory
- Fetches ECB historical USD/EUR exchange rates
- Categorizes each order as "Electronics" or "Other" based on item titles
- Converts prices to EUR using the order date's exchange rate, rounded up
- Outputs a formatted table to console and `orders_summary.csv`

### Verified
- Run: structure created, script syntax OK
