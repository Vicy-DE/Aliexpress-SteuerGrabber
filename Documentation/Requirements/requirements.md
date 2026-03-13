# Requirements — AliExpress-SteuerGrabber

## 1. Firefox Cookie Extraction — Browser Integration

| Item | Detail |
|---|---|
| **Module / Component** | grabber |
| **Interface** | Firefox profile / SQLite |
| **Dependencies** | sqlite3, configparser, shutil, tempfile (stdlib) |
| **Requirements** | - Auto-detect the default Firefox profile on Windows via `profiles.ini`. |
|  | - Copy `cookies.sqlite` to a temp directory to avoid lock conflicts with the running Firefox process. |
|  | - Extract all cookies matching `.aliexpress.com` domain. |
|  | - Convert Firefox cookie fields (host, name, value, path, expiry, isSecure, isHttpOnly, sameSite) to Playwright-compatible format. |
|  | - Abort with a clear error if no AliExpress cookies are found. |

## 2. Order Scraping — Web Automation

| Item | Detail |
|---|---|
| **Module / Component** | grabber |
| **Interface** | Browser automation (Playwright Firefox) |
| **Dependencies** | playwright |
| **Requirements** | - Inject extracted Firefox cookies into a new Playwright Firefox context. |
|  | - Navigate to AliExpress order list page. |
|  | - Try API interception (network response listener) first; fall back to DOM scraping. |
|  | - Handle pagination automatically (click "next" until no more pages). |
|  | - Extract: order ID, date, item titles, total price (USD). |
|  | - Visit order detail pages to enrich missing fields. |
|  | - Handle multiple AliExpress date formats (Jan 15 2025, 2025-01-15, 15.01.2025, etc.). |

## 3. Invoice PDF Download — File I/O

| Item | Detail |
|---|---|
| **Module / Component** | grabber |
| **Interface** | Browser automation / File I/O |
| **Dependencies** | playwright |
| **Requirements** | - Save invoice PDFs to `invoices/` directory with naming `<order_id>.pdf`. |
|  | - Skip download if the PDF already exists (idempotent). |
|  | - Try clicking invoice/receipt download button on the order detail page. |
|  | - Fall back to saving the order detail page as PDF (`page.pdf()`). |
|  | - Create the `invoices/` directory automatically if it does not exist. |

## 4. EUR Conversion — ECB Exchange Rates

| Item | Detail |
|---|---|
| **Module / Component** | grabber |
| **Interface** | HTTP API (ECB XML feed) |
| **Dependencies** | requests |
| **Requirements** | - Fetch ECB historical USD/EUR daily reference rates from the XML feed. |
|  | - Cache rates locally (`ecb_rates_cache.json`) for 24 hours. |
|  | - For each order, find the ECB rate matching the order date. |
|  | - If no rate exists for the exact date (weekend/holiday), use the nearest previous business day (up to 7 days back). |
|  | - Convert USD→EUR and round **up** to the next full cent (`math.ceil(eur * 100) / 100`). |
|  | - Return the rate used and the date it was from for traceability. |

## 5. Order Categorization — Electronics Classification

| Item | Detail |
|---|---|
| **Module / Component** | grabber |
| **Interface** | N/A (string matching) |
| **Dependencies** | N/A (stdlib only) |
| **Requirements** | - Classify each order as "Electronics" or "Other" based on item title keywords. |
|  | - Keyword list covers: passive components (resistor, capacitor, etc.), active components (IC, MCU, MOSFET), dev boards (Arduino, ESP32, STM32), test equipment (multimeter, oscilloscope), connectors, wiring, soldering supplies, 3D printing, CNC. |
|  | - Match is case-insensitive against the concatenated item titles. |
|  | - Any single keyword match classifies the entire order as "Electronics". |

## 6. CSV Export & Summary Table — Output

| Item | Detail |
|---|---|
| **Module / Component** | grabber |
| **Interface** | File I/O / Console |
| **Dependencies** | tabulate |
| **Requirements** | - Print a formatted table to the console using `tabulate` (grid format). |
|  | - Export to `orders_summary.csv` with semicolon delimiter (`;`). |
|  | - Columns: Order ID, Date, Items (truncated to 80 chars), Category, Price (USD), Rate (USD/EUR), Rate Date, Price (EUR). |
|  | - Print summary totals: Electronics total EUR, Other total EUR, Grand total EUR. |

---

## 7. Automotive Category — Classification

| Item | Detail |
|---|---|
| **Module / Component** | grabber |
| **Interface** | N/A (string matching) |
| **Dependencies** | N/A (stdlib only) |
| **Requirements** | - Orders matching automotive keywords (motorcycle, OBD, car diagnostic, etc.) are classified as "Automotive" instead of "Other". |
|  | - Automotive keywords take priority over electronics keywords. |
|  | - Three categories: "Electronics", "Automotive", "Other". |
|  | - Yearly summaries, order summaries, and CSV export reflect all three categories. |

## 8. Local Part Database — Component Identification

| Item | Detail |
|---|---|
| **Module / Component** | grabber |
| **Interface** | N/A (in-memory dict) |
| **Dependencies** | N/A (stdlib only) |
| **Requirements** | - Curated local database of ~80 common electronic components (MCUs, ICs, sensors, connectors, etc.). |
|  | - `lookup_part()` matches part numbers exactly first, then by prefix for chip families. |
|  | - Replaces Octopart search links in Markdown invoices and reports with actual manufacturer + description. |
|  | - Octopart report now shows local database results instead of external search links. |

## 9. PNG to PDF with Copyable Text — Invoice Fallback

| Item | Detail |
|---|---|
| **Module / Component** | grabber |
| **Interface** | File I/O |
| **Dependencies** | fpdf2, Pillow |
| **Requirements** | - When receipt extraction fails and a screenshot fallback is used, the generated PDF includes a text page with order data (order ID, date, category, items, total). |
|  | - The screenshot is embedded as a second page. |
|  | - Text on the first page is copyable (not an image). |
|  | - If no order data is available, only the screenshot page is created. |

---

## 10. Code Refactoring — Max 500 Lines Per File

| Item | Detail |
|---|---|
| **Module / Component** | All modules |
| **Interface** | N/A (internal restructuring) |
| **Dependencies** | N/A |
| **Requirements** | - Split `grabber.py` (currently ~1800 lines) into multiple modules under `utils/`. |
|  | - No single Python file may exceed 500 lines of code. |
|  | - `grabber.py` remains the main entry point (orchestration and `main()` only). |
|  | - New modules: `utils/config.py` (constants/keywords), `utils/exchange.py` (ECB rates), `utils/categorizer.py` (classification + part lookup), `utils/firefox.py` (cookie extraction), `utils/scraper.py` (order list scraping + parsing), `utils/receipt.py` (receipt data extraction), `utils/pdf_generator.py` (PDF creation + OCR verification), `utils/md_generator.py` (Markdown invoices), `utils/reports.py` (summaries + CSV export), `utils/downloader.py` (invoice download + batch processing). |
|  | - All existing tests must continue to pass after refactoring. |
|  | - No behaviour change — only structural reorganisation. |

## 11. Receipt Screenshot Matching — Original Format

| Item | Detail |
|---|---|
| **Module / Component** | grabber / receipt / pdf_generator |
| **Interface** | Browser automation / File I/O |
| **Dependencies** | playwright, fpdf2, pytesseract, opencv-python, Pillow |
| **Requirements** | - Downloaded receipts must visually match the AliExpress receipt page (same layout as `orginal/` reference screenshots). |
|  | - For 2023-2025 orders: ≥90% must produce a text-based PDF from receipt data extraction. Remaining orders fall back to screenshot-based PDF. |
|  | - PDF is created from the receipt screenshot image (not from MD). |
|  | - OCR text extraction from the screenshot image is compared against the MD content for validation. |
|  | - The PDF embeds the original screenshot image so it looks identical to the web page. |

## 12. 2017 Order Price Extraction — Legacy Orders

| Item | Detail |
|---|---|
| **Module / Component** | grabber / receipt / downloader |
| **Interface** | Browser automation |
| **Dependencies** | playwright, pytesseract, Pillow |
| **Requirements** | - For 2017-era orders where the tax-ui page has no structured receipt data, extract prices from the screenshot using OCR (Tesseract). |
|  | - Parse `US $X.XX` patterns from OCR'd text to populate `total_usd`. |
|  | - Fall back to order detail page scraping if OCR also fails. |

## 13. OCR-Based PDF Creation — Image-to-PDF Pipeline

| Item | Detail |
|---|---|
| **Module / Component** | pdf_generator |
| **Interface** | File I/O |
| **Dependencies** | fpdf2, pytesseract, opencv-python, Pillow |
| **Requirements** | - Create the fallback PDF from the screenshot image directly (not from the Markdown file). |
|  | - Use Tesseract OCR to detect and extract text from the screenshot image. |
|  | - The PDF shows the same picture as the original screenshot image. |
|  | - Extracted OCR text is compared against the Markdown content created from web scraping. |
|  | - If OCR text matches the MD content (key fields: order ID, total, items), mark the invoice as verified. |

## 14. Image-PDF Comparison Testing — Quality Verification

| Item | Detail |
|---|---|
| **Module / Component** | tests |
| **Interface** | N/A (test only) |
| **Dependencies** | opencv-python, Pillow, fpdf2, pytesseract |
| **Requirements** | - Convert the generated PDF back to an image. |
|  | - Compare the PDF-rendered image against the original screenshot at quarter resolution. |
|  | - Similarity must be ≥99% (structural similarity or pixel-level comparison). |
|  | - Test validates that the PDF faithfully reproduces the original screenshot. |
|  | - Test extracts text from the PDF-image via OCR and verifies it matches the MD file content. |

## 15. Branded PDF with Order Subfolders — Invoice Enhancement

| Item | Detail |
|---|---|
| **Module / Component** | downloader / pdf_generator / md_generator / reports / grabber |
| **Interface** | Browser automation / File I/O / HTTP (product images) |
| **Dependencies** | playwright, fpdf2, requests, Pillow |
| **Requirements** | - Restructure output to `invoices/<year>/<order_id>/` subfolders (one folder per order). |
|  | - Create `resources/` subfolder inside each order folder containing raw captured data: `detail_page.png` (detail page screenshot), `receipt_page.html` (tax-ui page HTML), and `product_N.{jpg,png}` (downloaded product images). |
|  | - Add EUR price with daily ECB exchange rate to the PDF text page (Total USD + Total EUR with rate and date). |
|  | - Add Octopart component identification to every electronics invoice PDF and MD: lookup in local PART_DATABASE; show manufacturer + description for known parts, Octopart search URL for unknown parts, "no matching part" for items without part numbers. |
|  | - Add product images to the PDF: extract image URLs from the detail page DOM, download up to 5 images via HTTP to resources/, embed up to 4 thumbnails (35×35px) on the PDF text page. |
|  | - Add AliExpress branded header to the PDF: orange banner (RGB 232,65,24) with white "AliExpress Order Invoice" text. |
|  | - Polish the Markdown format: table-based layout for metadata/items/financial summary, blockquote shipping/payment, EUR conversion table, Component Identification table with Octopart search links, dividers between sections, footer text. |

---

## Traceability Matrix

| Req # | Feature | Depends On |
|---|---|---|
| 1 | Firefox Cookie Extraction | — |
| 2 | Order Scraping | 1 |
| 3 | Invoice PDF Download | 2 |
| 4 | EUR Conversion | — |
| 5 | Order Categorization | 2 |
| 6 | CSV Export & Summary Table | 2, 4, 5 |
| 7 | Automotive Category | 5 |
| 8 | Local Part Database | 5 |
| 9 | PNG to PDF with Copyable Text | 3 |
| 10 | Code Refactoring | 1–9 |
| 11 | Receipt Screenshot Matching | 3, 13 |
| 12 | 2017 Order Price Extraction | 3, 13 |
| 13 | OCR-Based PDF Creation | 3 |
| 14 | Image-PDF Comparison Testing | 13 |
| 15 | Branded PDF with Order Subfolders | 3, 4, 5, 8 |
