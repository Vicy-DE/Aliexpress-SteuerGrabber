## [2026-03-09] Fix receipt extraction, add Octopart search, add parallel downloads

### What was changed
- `grabber.py` — Fixed CSS selectors in `extract_receipt_data()`: `summary--left`/`summary--right` (was `summary--label`/`summary--value`), `products--product--` (was `products--item`). Added `sku` field extraction. Fixed VAT/total ordering in extraction loop.
- `grabber.py` — Added `octopart_search_url()` to generate Octopart search URLs for component lookup.
- `grabber.py` — Added `generate_octopart_report()` to create a consolidated Markdown report with Octopart links for all electronics items.
- `grabber.py` — Updated `generate_invoice_md()` to include Octopart search links section for electronics orders.
- `grabber.py` — Added `_process_order_batch()` worker function for parallel order processing with dedicated headless browser instances.
- `grabber.py` — Updated `main()` to process orders in parallel using `concurrent.futures.ThreadPoolExecutor` (4 workers).
- `grabber.py` — Added imports: `concurrent.futures`, `urllib.parse.quote_plus`. Added constants: `OCTOPART_SEARCH_URL`, `MAX_WORKERS`.
- `tests/test_grabber.py` — Added `TestOctopartSearchUrl` (3 tests), `TestGenerateOctopartReport` (3 tests), `test_electronics_md_has_octopart_links` (1 test).

### Why it was changed
- Receipt extraction always fell back to screenshots because CSS selectors didn't match actual AliExpress class names.
- User requested Octopart search integration for electronics components.
- User requested parallel downloads to speed up processing of ~486 orders.

### What it does / expected behaviour
- Receipt data (order ID, items, totals, VAT) is correctly extracted from the tax-ui iframe — verified 10/10 consecutive successes on live orders.
- Electronics order invoices include clickable Octopart search links in the Markdown files.
- A consolidated `analysis/octopart_search.md` report lists all electronics items with Octopart URLs.
- Orders are processed in parallel (4 headless browser instances) instead of sequentially, reducing total processing time by ~4x.

### Verified
- Run: OK — `py -3 -m pytest tests/ -v` → 56 passed in 0.43s
- Live: Receipt extraction verified on 10 consecutive orders (diagnostic test)

## [2026-03-09] Add complete documentation framework, tests, and requirements

### What was changed
- `.github/instructions/documentation/TEST_DOC.instructions.md` — Test generation & documentation instructions (adapted from RC-Servo)
- `.github/instructions/documentation/TODO_DOC.instructions.md` — Todo documentation instructions (adapted from RC-Servo)
- `.github/instructions/documentation/REQUIREMENTS_DOC.instructions.md` — Requirements documentation instructions (adapted from RC-Servo)
- `.github/instructions/index.instructions.md` — Updated workflow with testing step and references to new instruction files
- `Documentation/Requirements/requirements.md` — Full requirements for all 6 features with traceability matrix
- `Documentation/ToDo/firefox-cookies.md` — Todo list (done) for Firefox cookie extraction
- `Documentation/ToDo/order-scraping.md` — Todo list (done) for order scraping
- `Documentation/ToDo/invoice-download.md` — Todo list (done) for invoice PDF download
- `Documentation/ToDo/eur-conversion.md` — Todo list (done) for EUR conversion
- `Documentation/ToDo/order-categorization.md` — Todo list (done) for order categorization
- `Documentation/ToDo/csv-export.md` — Todo list (done) for CSV export & summary table
- `tests/test_grabber.py` — 38 unit tests covering EUR conversion, date parsing, categorization, raw order parsing
- `Documentation/Tests/2026-03-09_initial-implementation.md` — Test report (38/38 pass)
- `requirements.txt` — Added pytest dependency
- `.gitignore` — Added `analysis/`, `orders_summary.csv`, `.pytest_cache/`

### Why it was changed
Establish complete project documentation structure following the RC-Servo pattern, with requirements, todos for implemented features, unit tests, and a tested workflow.

### What it does / expected behaviour
- Copilot follows the updated workflow: test → document → test report → commit
- All pure logic functions are covered by automated tests (38 pass)
- Requirements document tracks all 6 features with dependencies
- Todo files serve as implementation history for all completed features

### Verified
- Run: OK — `py -3 -m pytest tests/ -v` → 38 passed in 0.18s

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
