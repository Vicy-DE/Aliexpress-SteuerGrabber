## [2026-03-12] Refactor to multi-module architecture, add OCR pipeline and image-PDF comparison testing

### What was changed
- `grabber.py` — Rewritten from 1816-line monolith to 181-line thin main() orchestration; all logic delegated to utils/ modules.
- `utils/__init__.py` — Created package init.
- `utils/config.py` — Created (272 lines): all constants, paths, URLs, keywords, PART_DATABASE, PART_NUMBER_PATTERNS, TESSERACT_CMD.
- `utils/exchange.py` — Created (63 lines): load_ecb_rates(), usd_to_eur_rounded_up().
- `utils/categorizer.py` — Created (63 lines): categorize_order(), extract_part_numbers(), lookup_part().
- `utils/firefox.py` — Created (141 lines): find_firefox_profile(), extract_firefox_cookies().
- `utils/scraper.py` — Created (294 lines): parse_aliexpress_date(), parse_raw_order(), scrape_order_list(), scrape_orders_via_api().
- `utils/receipt.py` — Created (106 lines): extract_receipt_data() with browser-side JS.
- `utils/pdf_generator.py` — Created (363 lines): convert_png_to_pdf(), generate_invoice_pdf(), ocr_extract_text(), ocr_extract_price(), verify_ocr_against_md(), pdf_to_image(), compare_images_quarter_resolution().
- `utils/md_generator.py` — Created (105 lines): generate_invoice_md().
- `utils/reports.py` — Created (376 lines): build_summary_table(), export_csv(), generate_yearly_summary(), generate_order_summary(), copy_electronics_invoices(), generate_octopart_report(), generate_run_report(), print_summary().
- `utils/downloader.py` — Created (256 lines): download_invoice_from_detail_page(), enrich_and_download(), process_order_batch().
- `tests/test_grabber.py` — Updated imports from `grabber` to `utils.*` modules; updated monkeypatch target from `grabber.SCRIPT_DIR` to `utils.reports.SCRIPT_DIR`.
- `tests/test_ocr_pdf.py` — Created (190 lines): 15 new tests for OCR text extraction, price extraction, MD verification, image-PDF round-trip comparison at quarter resolution.
- `Documentation/Requirements/requirements.md` — Added Req #10-14 (Code Refactoring, Receipt Screenshot Matching, 2017 Order Price Extraction, OCR-Based PDF Creation, Image-PDF Comparison Testing).
- `Documentation/ToDo/refactor-ocr-pdf.md` — Created task checklist for the refactoring work.

### Why it was changed
- User requested: max 500 lines per file, OCR-based PDF creation from images, text detection + MD comparison, image-PDF round-trip testing at quarter resolution (≥99% similarity), 2017 order price extraction via OCR.

### What it does / expected behaviour
- No file exceeds 500 lines (largest: utils/reports.py at 376 lines, grabber.py at 181 lines).
- OCR pipeline: Tesseract extracts text from receipt screenshots; prices extracted via regex for 2017-era orders missing receipt data.
- verify_ocr_against_md() cross-checks OCR output (order ID, price, items) against companion MD file.
- compare_images_quarter_resolution() compares original image vs. PDF-extracted image at 25% resolution using pixel-wise similarity.
- 2017 orders: OCR price extraction fills in missing total_usd from screenshots.
- All 100 tests pass (85 existing + 15 new OCR/comparison tests).

### Verified
- Run: OK (100 tests pass)

## [2026-03-12] Automotive category, local part database, copyable-text fallback PDFs

### What was changed
- `grabber.py` — `categorize_order()` now returns "Automotive" (instead of "Other") for automotive keyword matches.
- `grabber.py` — Added `PART_DATABASE` constant with ~80 curated electronic components (MCUs, ICs, sensors, connectors, motor drivers, LEDs, power ICs).
- `grabber.py` — Added `lookup_part(part_number)` function for exact + prefix matching against the local database.
- `grabber.py` — Rewrote `convert_png_to_pdf()` — accepts optional `order` parameter; generates text page (order ID, date, category, items, total) + screenshot page.
- `grabber.py` — Updated `download_invoice_from_detail_page()` to pass `order` dict to `convert_png_to_pdf()` in fallback paths.
- `grabber.py` — Updated `generate_invoice_md()` — Component Identification now uses `lookup_part()` with manufacturer + description from local database.
- `grabber.py` — Rewrote `generate_octopart_report()` — shows Manufacturer + Description columns from local database instead of Octopart search links.
- `grabber.py` — Updated `generate_yearly_summary()` for 3 categories (Electronics, Automotive, Other) in both order table and totals.
- `grabber.py` — Updated `generate_order_summary()` for 3 categories.
- `grabber.py` — Updated `main()` summary stats to print Electronics, Automotive, and Other totals.
- `grabber.py` — Updated batch PNG→PDF in `main()` to pass matched order data for text-based fallback PDFs.
- `tests/test_grabber.py` — Updated all automotive tests from "Other" to "Automotive" (8 tests).
- `tests/test_grabber.py` — Added `TestLookupPart` (6 tests: exact, case-insensitive, prefix, unknown, diode, sensor).
- `tests/test_grabber.py` — Added `test_creates_pdf_with_order_data` for PNG→PDF with order parameter.
- `tests/test_grabber.py` — Updated Octopart report and Markdown invoice tests for new format.
- `Documentation/Requirements/requirements.md` — Added Req #7 (Automotive Category), #8 (Local Part Database), #9 (PNG-to-PDF Copyable Text).

### Why it was changed
- User requested: define an automotive category, remove Octopart search links and show one fitting result, convert PNG screenshots to PDF with copyable text.
- Prior behavior classified automotive items as "Other" — now correctly labeled "Automotive".
- Octopart API requires OAuth2 — replaced with curated local database of ~80 common electronic components.
- Fallback PDFs were screenshot-only — now include a text page with order data for copyable text.

### What it does / expected behaviour
- Three-category classification: Electronics, Automotive, Other.
- Fallback PDFs have 2 pages: page 1 with copyable order data text, page 2 with embedded screenshot.
- Electronics reports and Markdown invoices show manufacturer + description from the local part database.
- 2023-2026 invoices: 100% text-based PDF (0 screenshot fallbacks).
- Full rerun: 1070/1071 PDFs, 0 screenshots, 1 failure.

### Verified
- Run: OK (85 tests pass, full rerun successful)

## [2026-03-12] Automotive exclusion, part number extraction, PNG→PDF conversion, direct receipt URL

### What was changed
- `grabber.py` — Removed broad "cnc" from `ELECTRONICS_KEYWORDS`; replaced with "cnc machine", "cnc router".
- `grabber.py` — Added `AUTOMOTIVE_KEYWORDS` constant (~40 keywords: motorcycle, OBD, HEX V2, INPA, carburetor, exhaust, flex fuel, etc.).
- `grabber.py` — Rewrote `categorize_order()` to check automotive keywords first; items matching both automotive and electronics keywords are classified as "Other".
- `grabber.py` — Added `extract_part_numbers(title)` function with 40+ regex patterns for component identification (ESP32, STM32, ATmega, 1N4007, NE555, WS2812, etc.).
- `grabber.py` — Rewrote `generate_octopart_report()` to include extracted part numbers in a table format with Octopart search links.
- `grabber.py` — Updated `generate_invoice_md()` — "Component Identification" section replaces "Octopart Search", listing extracted part numbers.
- `grabber.py` — Added `convert_png_to_pdf(png_path, pdf_path)` using fpdf2 + PIL to embed screenshot PNGs in PDF format.
- `grabber.py` — Updated `download_invoice_from_detail_page()` — screenshot fallback now also converts PNG→PDF.
- `grabber.py` — Added batch PNG→PDF conversion step in `main()` after worker processing.
- `grabber.py` — Changed `extract_receipt_data()` to navigate directly to tax-ui URL instead of clicking Receipt button and waiting for iframe.
- `grabber.py` — Changed `MAX_WORKERS` from 4 to 2, `headless=False` for reliable receipt extraction.
- `tests/test_grabber.py` — Added `TestAutomotiveExclusion` (11 tests), `TestExtractPartNumbers` (8 tests), `TestConvertPngToPdf` (2 tests). Fixed "Octopart Search" → "Component Identification" assertion.

### Why it was changed
- Car diagnostic tools (HEX V2, OBD scanners, Openport ECU Flash) and motorcycle parts were incorrectly categorized as "Electronics" because they matched broad keywords like "stm32", "programmer", "sensor", "relay".
- Octopart report needed real part number extraction instead of just search links with full item titles.
- Invoice screenshots (PNG) needed conversion to PDF for consistent tax documentation format.
- Receipt extraction via iframe detection failed silently in headed mode; direct URL navigation is 100% reliable.

### What it does / expected behaviour
- 255 electronics orders correctly identified (down from ~280+ with false positives).
- All automotive/motorcycle/OBD/diagnostic items categorized as "Other".
- Octopart report shows extracted part numbers (ATMEGA328P, ESP8266, 2N7000, SSD1306, etc.) with search links.
- Full rerun: 1071 orders → 1071 PDFs, 0 screenshots, 0 failures (100% success rate).

### Verified
- Run: OK — `py -3 -m pytest tests/ -v` → 78 passed in 0.87s
- Live: Full rerun — 1071/1071 PDFs generated, 100% success rate

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
