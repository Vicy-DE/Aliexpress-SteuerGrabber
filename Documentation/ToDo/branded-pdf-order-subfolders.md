# Todo: Branded PDF with Order Subfolders

**Created:** 2026-03-13
**Requirement:** [Req #15 — Branded PDF with Order Subfolders](../Requirements/requirements.md)
**Status:** Done

---

## Tasks

- [x] Restructure output to `invoices/<year>/<order_id>/` subfolders
  - [x] Modify `utils/downloader.py` path construction
  - [x] Update `utils/reports.py` copy_electronics_invoices path
  - [x] Update `grabber.py` PNG-to-PDF conversion loop
- [x] Create `resources/` subfolder with raw captured data
  - [x] Save detail page screenshot to `resources/detail_page.png`
  - [x] Save receipt page HTML to `resources/receipt_page.html`
  - [x] Download product images to `resources/product_N.{jpg,png}`
- [x] Add EUR price with daily ECB rate to PDF
  - [x] Expand `convert_png_to_pdf()` signature with `ecb_rates` param
  - [x] Add EUR conversion section to `_add_text_page()`
- [x] Add Octopart results to electronics invoices
  - [x] Add `_add_octopart_section()` to `utils/pdf_generator.py`
  - [x] Add Component Identification table to `utils/md_generator.py`
- [x] Add product images and AliExpress logo to PDF
  - [x] Extract image URLs from detail page DOM
  - [x] Add `_download_product_images()` to `utils/downloader.py`
  - [x] Embed product image thumbnails in `_add_text_page()`
  - [x] Add branded orange header to `_add_text_page()`
- [x] Polish Markdown format
  - [x] Table-based metadata, items, financial summary
  - [x] Blockquote shipping/payment
  - [x] EUR conversion table
  - [x] Octopart search links
  - [x] Dividers and footer
- [x] Add `imageUrl` extraction to `utils/receipt.py` JS
- [x] Tests pass (`py -3 -m pytest tests/ -v`) — 100 passed
- [x] Full script run completes successfully
- [x] CHANGE_LOG.md updated
- [x] PROJECT_DOC.md updated
- [x] requirements.md updated

---

## Notes

- Product image extraction uses separate JS call on detail page (not inside enrichment block) to capture images for all orders.
- AliExpress logo implemented as FPDF drawing (orange rect + white text) — no external image file needed.
- Deferred imports in `_add_text_page` and `_add_octopart_section` avoid circular dependencies.
- `requests.get()` used for product image download (CDN URLs are public, no auth needed).
