"""Invoice download, order enrichment and parallel batch processing.

Handles navigating to order detail pages, extracting receipt data,
generating PDF + MD invoices, and processing order batches in parallel
browser instances.
"""

import logging
import re
import time

from playwright.sync_api import sync_playwright

from utils.categorizer import categorize_order
from utils.config import (
    ALIEXPRESS_ORDER_DETAIL_URL,
    INVOICES_DIR,
)
from utils.md_generator import generate_invoice_md
from utils.pdf_generator import (
    convert_png_to_pdf,
    generate_invoice_pdf,
    ocr_extract_price,
)
from utils.receipt import extract_receipt_data
from utils.scraper import parse_aliexpress_date


def download_invoice_from_detail_page(page, order, ecb_rates):
    """Extract receipt data and generate PDF + MD.

    The page must already be on the order detail page.
    Uses the tax-ui page to extract structured data, then generates
    a PDF with copyable text and a companion Markdown invoice file.

    Args:
        page: Playwright page object.
        order: Order dict.
        ecb_rates: ECB exchange rate dict.

    Returns:
        Path to saved PDF, or None if download failed.
    """
    order_id = order["order_id"]
    date_str = order.get("date", "unknown")
    year = date_str[:4] if len(date_str) >= 4 else "unknown"

    year_dir = INVOICES_DIR / year
    year_dir.mkdir(parents=True, exist_ok=True)

    filename_base = f"{date_str}-{order_id}"
    pdf_path = year_dir / f"{filename_base}.pdf"
    md_path = year_dir / f"{filename_base}.md"
    png_path = year_dir / f"{filename_base}.png"

    if pdf_path.exists():
        print(f"  Invoice {filename_base}.pdf already exists, skipping.")
        return pdf_path

    # Extract receipt data from the tax-ui page
    receipt_data = extract_receipt_data(page, order_id)

    if receipt_data:
        # Take a screenshot of the receipt page for the image-based PDF
        try:
            page.screenshot(path=str(png_path), full_page=True)
        except Exception:
            pass

        # Generate PDF from the screenshot image (primary)
        if png_path.exists():
            convert_png_to_pdf(png_path, pdf_path, order=order)
        else:
            # Fallback: text-only PDF
            generate_invoice_pdf(receipt_data, pdf_path)

        print(f"  Generated PDF invoice: {filename_base}.pdf")
        generate_invoice_md(receipt_data, order, md_path, ecb_rates)
        print(f"  Generated MD invoice:  {filename_base}.md")
        return pdf_path

    # Fallback: screenshot of the detail page
    if png_path.exists():
        converted = convert_png_to_pdf(png_path, pdf_path, order=order)
        if converted:
            # Try OCR price extraction for old orders
            if order.get("total_usd", 0) == 0:
                ocr_price = ocr_extract_price(png_path)
                if ocr_price > 0:
                    order["total_usd"] = ocr_price
            print(f"  Converted existing screenshot to PDF: {filename_base}.pdf")
            return pdf_path
        print(f"  Screenshot {filename_base}.png already exists, skipping.")
        return png_path

    try:
        detail_url = ALIEXPRESS_ORDER_DETAIL_URL.format(order_id=order_id)
        page.goto(detail_url)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        page.screenshot(path=str(png_path), full_page=True)

        # Try OCR price extraction for old orders missing price
        if order.get("total_usd", 0) == 0:
            ocr_price = ocr_extract_price(png_path)
            if ocr_price > 0:
                order["total_usd"] = ocr_price

        convert_png_to_pdf(png_path, pdf_path, order=order)
        generate_invoice_md(None, order, md_path, ecb_rates)
        print(f"  Saved screenshot+PDF for order {order_id}")
        return pdf_path
    except Exception as e:
        print(f"  Could not save screenshot for order {order_id}: {e}")
        return None


def enrich_and_download(page, order, ecb_rates):
    """Navigate to order detail, enrich data, and download invoice.

    Combines enrichment and receipt extraction in a single navigation.

    Args:
        page: Playwright page object.
        order: Order dict.
        ecb_rates: ECB exchange rate dict.

    Returns:
        Tuple of (updated_order, pdf_path_or_None).
    """
    detail_url = ALIEXPRESS_ORDER_DETAIL_URL.format(
        order_id=order["order_id"]
    )
    page.goto(detail_url)
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Enrich missing fields from the detail page
    if not order["total_usd"] or not order["items"] or not order["date"]:
        detail = page.evaluate("""() => {
            const result = {items: [], total_text: '', date: ''};
            document.querySelectorAll(
                '.order-item-content-info-name, '
                + '[class*="product-title"], [class*="item-title"]'
            ).forEach(el => result.items.push(el.textContent.trim()));
            const priceEl = document.querySelector(
                '.order-item-content-opt-price-total, '
                + '[class*="total-price"], [class*="order-amount"]'
            );
            if (priceEl) result.total_text = priceEl.textContent.trim();
            const headerEl = document.querySelector('.order-item-header');
            if (headerEl) {
                const dateMatch = headerEl.textContent.match(
                    /Order date:\\s*([A-Za-z]+ \\d{1,2},\\s*\\d{4})/
                );
                if (dateMatch) result.date = dateMatch[1];
            }
            if (!result.date) {
                const dateEl = document.querySelector(
                    '[class*="order-time"], [class*="order-date"], '
                    + '[class*="pay-time"]'
                );
                if (dateEl) result.date = dateEl.textContent.trim();
            }
            return result;
        }""")

        if not order["items"] and detail["items"]:
            order["items"] = detail["items"]
        if order["total_usd"] == 0 and detail["total_text"]:
            price_match = re.search(
                r"[\d]+[.,]?\d*", detail["total_text"].replace(",", "")
            )
            if price_match:
                order["total_usd"] = float(
                    price_match.group().replace(",", ".")
                )
        if not order["date"] and detail["date"]:
            order["date"] = parse_aliexpress_date(detail["date"])

        order["category"] = categorize_order(order["items"])

    pdf_path = download_invoice_from_detail_page(page, order, ecb_rates)
    return order, pdf_path


def process_order_batch(batch_args):
    """Process a batch of orders in a dedicated Playwright browser.

    Each worker launches its own headed Firefox with injected cookies,
    processes its assigned orders, and returns the results.

    Args:
        batch_args: Tuple of (orders_batch, firefox_cookies,
                    ecb_rates, worker_id).

    Returns:
        List of (order, pdf_path_or_None) tuples.
    """
    orders_batch, firefox_cookies, ecb_rates, worker_id = batch_args

    results = []
    retry_queue = []

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            accept_downloads=True,
        )
        context.add_cookies(firefox_cookies)
        page = context.new_page()

        for order in orders_batch:
            try:
                order, pdf_path = enrich_and_download(
                    page, order, ecb_rates
                )
                if pdf_path and str(pdf_path).endswith(".pdf"):
                    results.append((order, pdf_path))
                    logging.info(
                        "[W%d] ✓ Order %s (PDF)",
                        worker_id, order["order_id"],
                    )
                elif pdf_path:
                    results.append((order, pdf_path))
                    logging.info(
                        "[W%d] 📷 Order %s (screenshot)",
                        worker_id, order["order_id"],
                    )
                elif order.get("date", "").startswith("2026"):
                    retry_queue.append(order)
                    logging.info(
                        "[W%d] ⟳ Order %s (2026, will retry)",
                        worker_id, order["order_id"],
                    )
                else:
                    results.append((order, None))
                    logging.info(
                        "[W%d] ⚠ Order %s (no output)",
                        worker_id, order["order_id"],
                    )
            except Exception as e:
                if order.get("date", "").startswith("2026"):
                    retry_queue.append(order)
                    logging.info(
                        "[W%d] ⟳ Order %s error, will retry: %s",
                        worker_id, order["order_id"], e,
                    )
                else:
                    logging.info(
                        "[W%d] ✗ Order %s: %s",
                        worker_id, order["order_id"], e,
                    )
                    results.append((order, None))
            time.sleep(1)

        context.close()
        browser.close()

        # Retry failed 2026 orders with a fresh browser
        if retry_queue:
            logging.info(
                "[W%d] Retrying %d failed 2026 orders...",
                worker_id, len(retry_queue),
            )
            browser = p.firefox.launch(headless=False)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                accept_downloads=True,
            )
            context.add_cookies(firefox_cookies)
            page = context.new_page()

            for order in retry_queue:
                try:
                    order, pdf_path = enrich_and_download(
                        page, order, ecb_rates
                    )
                    results.append((order, pdf_path))
                    is_pdf = pdf_path and str(pdf_path).endswith(".pdf")
                    status = "✓" if is_pdf else "📷" if pdf_path else "⚠"
                    logging.info(
                        "[W%d] %s Order %s (retry)",
                        worker_id, status, order["order_id"],
                    )
                except Exception as e:
                    logging.info(
                        "[W%d] ✗ Order %s retry failed: %s",
                        worker_id, order["order_id"], e,
                    )
                    results.append((order, None))
                time.sleep(2)

            context.close()
            browser.close()

    return results
