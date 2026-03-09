"""AliExpress invoice grabber and order categorizer.

Downloads all invoice PDFs from AliExpress completed orders,
categorizes them (electronics vs. other), converts prices to EUR
using ECB historical exchange rates, and outputs a summary CSV.
"""

import csv
import json
import math
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from tabulate import tabulate

SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
INVOICES_DIR = SCRIPT_DIR / "invoices"
STATE_FILE = SCRIPT_DIR / "browser_state.json"
OUTPUT_CSV = SCRIPT_DIR / "orders_summary.csv"

ALIEXPRESS_ORDER_LIST_URL = "https://www.aliexpress.com/p/order/index.html"
ALIEXPRESS_ORDER_DETAIL_URL = "https://www.aliexpress.com/p/order/detail.html?orderId={order_id}"

# ECB daily exchange rate XML feed (last 90 days)
ECB_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
ECB_NS = {"gesmes": "http://www.gesmes.org/xml/2002-08-01",
           "ecb": "http://www.ecb.int/vocabulary/2002-08-01"}

# Keywords indicating electronic parts or equipment
ELECTRONICS_KEYWORDS = [
    "pcb", "circuit", "board", "resistor", "capacitor", "inductor", "diode",
    "transistor", "mosfet", "igbt", "led", "ic ", " ic", "chip", "microcontroller",
    "mcu", "arduino", "esp32", "esp8266", "stm32", "raspberry", "sensor",
    "module", "relay", "transformer", "voltage regulator", "power supply",
    "oscillator", "crystal", "connector", "header", "pin", "socket",
    "soldering", "solder", "flux", "multimeter", "oscilloscope", "logic analyzer",
    "programmer", "debugger", "servo", "motor", "driver", "stepper",
    "battery", "charger", "buck", "boost", "converter", "adapter",
    "wire", "cable", "dupont", "breadboard", "prototype", "jumper",
    "fuse", "switch", "button", "potentiometer", "encoder", "display",
    "oled", "lcd", "tft", "uart", "spi", "i2c", "usb", "serial",
    "antenna", "rf", "wireless", "bluetooth", "wifi", "lora",
    "heat sink", "heatsink", "thermal", "fan", "cooling",
    "3d print", "cnc", "laser", "engraver",
    "electronic", "electrical", "component", "semiconductor",
    "amplifier", "op-amp", "opamp", "comparator",
    "voltmeter", "ammeter", "wattmeter", "clamp meter",
    "crimping", "terminal", "ferrule", "shrink tube", "heat shrink",
    "oscillator", "timer", "555", "fpga", "cpld", "eeprom", "flash",
    "smd", "through hole", "dip", "sop", "qfp", "bga",
]


def load_ecb_rates():
    """Fetch ECB historical USD/EUR exchange rates.

    Returns:
        Dict mapping date string (YYYY-MM-DD) to USD-per-EUR rate (float).
    """
    cache_file = SCRIPT_DIR / "ecb_rates_cache.json"

    # Use cache if less than 24h old
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < 86400:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

    print("Fetching ECB exchange rates...")
    resp = requests.get(ECB_RATES_URL, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    rates = {}

    for cube_time in root.findall(".//ecb:Cube[@time]", ECB_NS):
        date_str = cube_time.attrib["time"]
        for cube_rate in cube_time.findall("ecb:Cube[@currency='USD']", ECB_NS):
            rates[date_str] = float(cube_rate.attrib["rate"])

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(rates, f)

    print(f"  Loaded {len(rates)} daily rates from ECB.")
    return rates


def usd_to_eur_rounded_up(usd_amount, order_date_str, ecb_rates):
    """Convert USD to EUR using ECB rate for the order date, rounded up.

    Uses the ECB daily reference rate. If the exact date has no rate
    (weekend/holiday), uses the nearest previous business day's rate.

    Args:
        usd_amount: Price in USD.
        order_date_str: Date string in YYYY-MM-DD format.
        ecb_rates: Dict of date -> USD-per-EUR rates from ECB.

    Returns:
        Tuple of (eur_amount_rounded_up, rate_used, rate_date_used).
    """
    date = datetime.strptime(order_date_str, "%Y-%m-%d")

    # Find nearest available rate (go back up to 7 days for holidays)
    for delta in range(8):
        check_date = (date - timedelta(days=delta)).strftime("%Y-%m-%d")
        if check_date in ecb_rates:
            usd_per_eur = ecb_rates[check_date]
            eur = usd_amount / usd_per_eur
            # Round up to next cent
            eur_rounded = math.ceil(eur * 100) / 100
            return eur_rounded, usd_per_eur, check_date

    # Fallback: if no rate found in the last 7 days, use the most recent rate
    sorted_dates = sorted(ecb_rates.keys(), reverse=True)
    if sorted_dates:
        fallback_date = sorted_dates[0]
        usd_per_eur = ecb_rates[fallback_date]
        eur = usd_amount / usd_per_eur
        eur_rounded = math.ceil(eur * 100) / 100
        return eur_rounded, usd_per_eur, fallback_date

    return usd_amount, 1.0, order_date_str  # Last resort: assume 1:1


def categorize_order(item_titles):
    """Categorize an order as electronics or non-electronics.

    Args:
        item_titles: List of item title strings from the order.

    Returns:
        "Electronics" if any item matches electronics keywords, else "Other".
    """
    combined = " ".join(item_titles).lower()
    for keyword in ELECTRONICS_KEYWORDS:
        if keyword in combined:
            return "Electronics"
    return "Other"


def save_browser_state(context):
    """Save browser cookies and storage state for session reuse.

    Args:
        context: Playwright browser context.
    """
    context.storage_state(path=str(STATE_FILE))
    print("Browser state saved.")


def wait_for_manual_login(page):
    """Wait for the user to manually log in to AliExpress.

    Args:
        page: Playwright page object.
    """
    print("\n" + "=" * 60)
    print("MANUAL LOGIN REQUIRED")
    print("=" * 60)
    print("A browser window has opened. Please log in to AliExpress.")
    print("After logging in, navigate to your orders page.")
    print("The script will continue automatically once logged in.")
    print("=" * 60 + "\n")

    # Wait until we see the order list page or the user avatar
    while True:
        try:
            page.wait_for_url("**/p/order/index.html**", timeout=5000)
            break
        except Exception:
            try:
                # Check if logged in by looking for buyer info
                if page.locator("[class*='avatar']").count() > 0:
                    page.goto(ALIEXPRESS_ORDER_LIST_URL)
                    page.wait_for_load_state("networkidle")
                    break
            except Exception:
                pass
            time.sleep(1)

    print("Login detected! Continuing...")


def scrape_order_list(page):
    """Scrape all orders from the AliExpress order list pages.

    Args:
        page: Playwright page on the order list.

    Returns:
        List of order dicts with keys: order_id, date, items, total_usd.
    """
    orders = []
    page_num = 1

    while True:
        print(f"Scraping order page {page_num}...")
        page.wait_for_load_state("networkidle")
        time.sleep(2)  # Allow dynamic content to load

        # Extract orders from current page
        order_cards = page.locator("[class*='order-item']").all()
        if not order_cards:
            # Try alternative selectors
            order_cards = page.locator("[class*='order-card']").all()
        if not order_cards:
            order_cards = page.locator("[class*='order-item-wraper']").all()

        if not order_cards:
            # Fallback: parse via JavaScript
            page_orders = page.evaluate("""() => {
                const orders = [];
                // Look for order containers with various class patterns
                const containers = document.querySelectorAll(
                    '[class*="order-item"], [class*="order-card"], [class*="order-item-wraper"], .order-item'
                );
                containers.forEach(container => {
                    const orderIdEl = container.querySelector(
                        '[class*="order-no"] span, [class*="id-text"], [class*="order-id"]'
                    );
                    const dateEl = container.querySelector(
                        '[class*="order-time"], [class*="order-date"], [class*="pay-time"]'
                    );
                    const priceEl = container.querySelector(
                        '[class*="order-amount"] span, [class*="total-price"], [class*="order-price"]'
                    );
                    const titleEls = container.querySelectorAll(
                        '[class*="product-title"], [class*="item-title"], [class*="product-name"]'
                    );

                    const titles = [];
                    titleEls.forEach(el => titles.push(el.textContent.trim()));

                    if (orderIdEl) {
                        orders.push({
                            order_id: orderIdEl.textContent.trim().replace(/[^0-9]/g, ''),
                            date: dateEl ? dateEl.textContent.trim() : '',
                            total_text: priceEl ? priceEl.textContent.trim() : '',
                            items: titles
                        });
                    }
                });
                return orders;
            }""")

            for o in page_orders:
                order = parse_raw_order(o)
                if order and order["order_id"]:
                    orders.append(order)
        else:
            for card in order_cards:
                order = extract_order_from_card(card)
                if order and order["order_id"]:
                    orders.append(order)

        print(f"  Found {len(orders)} orders so far.")

        # Check for next page
        next_btn = page.locator("button[class*='next']").first
        if next_btn.count() > 0 and next_btn.is_enabled():
            next_btn.click()
            page_num += 1
            time.sleep(2)
        else:
            # Try alternative pagination
            next_link = page.locator("a[class*='next']").first
            if next_link.count() > 0:
                next_link.click()
                page_num += 1
                time.sleep(2)
            else:
                break

    return orders


def extract_order_from_card(card):
    """Extract order data from a single order card element.

    Args:
        card: Playwright locator for one order card.

    Returns:
        Dict with order_id, date, items, total_usd or None.
    """
    try:
        order_id = ""
        date_str = ""
        total_text = ""
        items = []

        # Try to extract order ID
        id_el = card.locator("[class*='order-no'], [class*='id-text'], [class*='order-id']").first
        if id_el.count() > 0:
            order_id = re.sub(r"[^0-9]", "", id_el.text_content())

        # Try to extract date
        date_el = card.locator("[class*='order-time'], [class*='order-date'], [class*='pay-time']").first
        if date_el.count() > 0:
            date_str = date_el.text_content().strip()

        # Try to extract price
        price_el = card.locator("[class*='order-amount'], [class*='total-price'], [class*='order-price']").first
        if price_el.count() > 0:
            total_text = price_el.text_content().strip()

        # Try to extract item titles
        title_els = card.locator("[class*='product-title'], [class*='item-title'], [class*='product-name']").all()
        for el in title_els:
            items.append(el.text_content().strip())

        return parse_raw_order({
            "order_id": order_id,
            "date": date_str,
            "total_text": total_text,
            "items": items
        })
    except Exception as e:
        print(f"  Warning: could not extract order from card: {e}")
        return None


def parse_raw_order(raw):
    """Parse raw order data into a standardized dict.

    Args:
        raw: Dict with order_id, date, total_text, items.

    Returns:
        Dict with order_id, date (YYYY-MM-DD), items, total_usd.
    """
    order_id = raw.get("order_id", "").strip()
    date_raw = raw.get("date", "").strip()
    total_text = raw.get("total_text", "").strip()
    items = raw.get("items", [])

    # Parse price — extract numeric value
    price_match = re.search(r"[\d]+[.,]?\d*", total_text.replace(",", ""))
    total_usd = float(price_match.group().replace(",", ".")) if price_match else 0.0

    # Parse date — AliExpress uses various formats
    date_str = parse_aliexpress_date(date_raw)

    return {
        "order_id": order_id,
        "date": date_str,
        "items": items,
        "total_usd": total_usd,
    }


def parse_aliexpress_date(date_raw):
    """Parse various AliExpress date formats to YYYY-MM-DD.

    Args:
        date_raw: Raw date string from AliExpress.

    Returns:
        Date string in YYYY-MM-DD format, or the raw string if parsing fails.
    """
    date_raw = date_raw.strip()
    # Remove common prefixes
    for prefix in ["Order date:", "Paid on", "Payment date:", "Date:"]:
        date_raw = date_raw.replace(prefix, "").strip()

    formats = [
        "%b %d, %Y",     # "Jan 15, 2025"
        "%B %d, %Y",     # "January 15, 2025"
        "%Y-%m-%d",      # "2025-01-15"
        "%d %b %Y",      # "15 Jan 2025"
        "%d/%m/%Y",      # "15/01/2025"
        "%m/%d/%Y",      # "01/15/2025"
        "%Y.%m.%d",      # "2025.01.15"
        "%d.%m.%Y",      # "15.01.2025"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try regex extraction
    match = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", date_raw)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"

    return date_raw


def download_invoice_from_detail_page(page, order_id):
    """Navigate to order detail and download the invoice PDF.

    Args:
        page: Playwright page object.
        order_id: AliExpress order ID string.

    Returns:
        Path to saved PDF, or None if download failed.
    """
    INVOICES_DIR.mkdir(exist_ok=True)
    pdf_path = INVOICES_DIR / f"{order_id}.pdf"

    if pdf_path.exists():
        print(f"  Invoice {order_id}.pdf already exists, skipping.")
        return pdf_path

    detail_url = ALIEXPRESS_ORDER_DETAIL_URL.format(order_id=order_id)
    page.goto(detail_url)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Look for invoice/receipt download button
    invoice_btn = None
    for selector in [
        "text=Invoice",
        "text=invoice",
        "text=Receipt",
        "text=receipt",
        "text=Download Invoice",
        "text=View Invoice",
        "[class*='invoice']",
        "a[href*='invoice']",
    ]:
        btn = page.locator(selector).first
        if btn.count() > 0:
            invoice_btn = btn
            break

    if invoice_btn:
        try:
            with page.expect_download(timeout=15000) as download_info:
                invoice_btn.click()
            download = download_info.value
            download.save_as(str(pdf_path))
            print(f"  Downloaded invoice for order {order_id}")
            return pdf_path
        except Exception:
            pass

    # Fallback: print the order detail page as PDF
    try:
        page.pdf(path=str(pdf_path), format="A4", print_background=True)
        print(f"  Saved order detail as PDF for order {order_id}")
        return pdf_path
    except Exception as e:
        # page.pdf() only works in headless Chromium
        print(f"  Could not save PDF for order {order_id}: {e}")
        return None


def enrich_order_from_detail(page, order):
    """Navigate to order detail page to fill in missing data.

    Args:
        page: Playwright page object.
        order: Order dict that may have missing fields.

    Returns:
        Updated order dict.
    """
    if order["total_usd"] > 0 and order["items"] and order["date"]:
        return order

    detail_url = ALIEXPRESS_ORDER_DETAIL_URL.format(order_id=order["order_id"])
    page.goto(detail_url)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    detail = page.evaluate("""() => {
        const result = {items: [], total_text: '', date: ''};

        // Item titles
        document.querySelectorAll(
            '[class*="product-title"], [class*="item-title"], [class*="product-name"]'
        ).forEach(el => result.items.push(el.textContent.trim()));

        // Total price
        const priceEl = document.querySelector(
            '[class*="order-amount"], [class*="total-price"], [class*="order-price"], [class*="total-amount"]'
        );
        if (priceEl) result.total_text = priceEl.textContent.trim();

        // Date
        const dateEl = document.querySelector(
            '[class*="order-time"], [class*="order-date"], [class*="pay-time"], [class*="create-time"]'
        );
        if (dateEl) result.date = dateEl.textContent.trim();

        return result;
    }""")

    if not order["items"] and detail["items"]:
        order["items"] = detail["items"]

    if order["total_usd"] == 0 and detail["total_text"]:
        price_match = re.search(r"[\d]+[.,]?\d*", detail["total_text"].replace(",", ""))
        if price_match:
            order["total_usd"] = float(price_match.group().replace(",", "."))

    if not order["date"] and detail["date"]:
        order["date"] = parse_aliexpress_date(detail["date"])

    return order


def scrape_orders_via_api(page):
    """Try to scrape orders via AliExpress API intercepted from network.

    Args:
        page: Playwright page object.

    Returns:
        List of order dicts, or empty list if API interception fails.
    """
    orders = []
    api_responses = []

    def handle_response(response):
        url = response.url
        if "orderList" in url or "order/list" in url or "api/order" in url:
            try:
                body = response.json()
                api_responses.append(body)
            except Exception:
                pass

    page.on("response", handle_response)
    page.goto(ALIEXPRESS_ORDER_LIST_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Process captured API responses
    for resp_body in api_responses:
        try:
            order_list = None
            # Navigate common API response structures
            if isinstance(resp_body, dict):
                for key in ["data", "result", "body"]:
                    if key in resp_body:
                        inner = resp_body[key]
                        if isinstance(inner, dict):
                            for inner_key in ["orderList", "orders", "list"]:
                                if inner_key in inner:
                                    order_list = inner[inner_key]
                                    break
                        elif isinstance(inner, list):
                            order_list = inner
                    if order_list:
                        break

            if order_list and isinstance(order_list, list):
                for api_order in order_list:
                    order = {
                        "order_id": str(api_order.get("orderId", api_order.get("id", ""))),
                        "date": "",
                        "items": [],
                        "total_usd": 0.0,
                    }

                    # Date
                    for date_key in ["orderDate", "createDate", "gmtCreate", "payTime"]:
                        if date_key in api_order:
                            order["date"] = parse_aliexpress_date(str(api_order[date_key]))
                            break

                    # Price
                    for price_key in ["totalAmount", "orderAmount", "totalPrice"]:
                        if price_key in api_order:
                            val = api_order[price_key]
                            if isinstance(val, (int, float)):
                                order["total_usd"] = float(val)
                            elif isinstance(val, str):
                                m = re.search(r"[\d.]+", val)
                                if m:
                                    order["total_usd"] = float(m.group())
                            break

                    # Items
                    for items_key in ["productList", "items", "orderItems", "childOrderList"]:
                        if items_key in api_order:
                            for item in api_order[items_key]:
                                for title_key in ["productName", "title", "name", "itemTitle"]:
                                    if title_key in item:
                                        order["items"].append(item[title_key])
                                        break

                    if order["order_id"]:
                        orders.append(order)
        except Exception:
            continue

    page.remove_listener("response", handle_response)
    return orders


def build_summary_table(orders, ecb_rates):
    """Build the categorized summary table with EUR conversion.

    Args:
        orders: List of order dicts.
        ecb_rates: ECB exchange rate dict.

    Returns:
        List of row dicts for the summary table.
    """
    rows = []
    for order in orders:
        category = categorize_order(order["items"])
        eur_amount, rate, rate_date = usd_to_eur_rounded_up(
            order["total_usd"], order["date"], ecb_rates
        )
        rows.append({
            "Order ID": order["order_id"],
            "Date": order["date"],
            "Items": "; ".join(order["items"])[:80] if order["items"] else "(no title)",
            "Category": category,
            "Price (USD)": f"${order['total_usd']:.2f}",
            "Rate (USD/EUR)": f"{rate:.4f}",
            "Rate Date": rate_date,
            "Price (EUR)": f"€{eur_amount:.2f}",
        })
    return rows


def export_csv(rows):
    """Export the summary table to CSV.

    Args:
        rows: List of row dicts.
    """
    if not rows:
        print("No orders to export.")
        return

    fieldnames = list(rows[0].keys())
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCSV exported to: {OUTPUT_CSV}")


def main():
    """Run the full AliExpress invoice grabber workflow."""
    load_dotenv(SCRIPT_DIR / ".env")

    ecb_rates = load_ecb_rates()

    print("Starting browser...")
    with sync_playwright() as p:
        # Use persistent context to keep login state
        browser_args = {
            "headless": False,
            "channel": "chromium",
        }

        if STATE_FILE.exists():
            context = p.chromium.launch_persistent_context(
                str(SCRIPT_DIR / "browser_data"),
                **browser_args,
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(ALIEXPRESS_ORDER_LIST_URL)
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Check if still logged in
            if "login" in page.url.lower():
                wait_for_manual_login(page)
                save_browser_state(context)
        else:
            context = p.chromium.launch_persistent_context(
                str(SCRIPT_DIR / "browser_data"),
                **browser_args,
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(ALIEXPRESS_ORDER_LIST_URL)
            page.wait_for_load_state("networkidle")
            wait_for_manual_login(page)
            save_browser_state(context)

        # Switch to "Completed" orders tab if available
        for tab_text in ["Completed", "Abgeschlossen", "Finished"]:
            tab = page.locator(f"text={tab_text}").first
            if tab.count() > 0:
                tab.click()
                time.sleep(2)
                break

        # Try API-based scraping first, fall back to DOM scraping
        print("\nScraping orders...")
        orders = scrape_orders_via_api(page)
        if not orders:
            orders = scrape_order_list(page)

        if not orders:
            print("No orders found. The page structure may have changed.")
            print("Please check the browser window and ensure you're on the orders page.")
            context.close()
            return

        print(f"\nFound {len(orders)} orders total.")

        # Enrich orders with missing data and download invoices
        for i, order in enumerate(orders):
            print(f"\nProcessing order {i + 1}/{len(orders)}: {order['order_id']}")

            # Fill in missing data from detail page
            order = enrich_order_from_detail(page, order)
            orders[i] = order

            # Download invoice
            download_invoice_from_detail_page(page, order["order_id"])

            # Be polite to the server
            time.sleep(1)

        save_browser_state(context)
        context.close()

    # Build and display summary
    rows = build_summary_table(orders, ecb_rates)

    print("\n" + "=" * 100)
    print("ORDER SUMMARY")
    print("=" * 100)
    print(tabulate(rows, headers="keys", tablefmt="grid"))

    # Summary statistics
    electronics_total_eur = sum(
        float(r["Price (EUR)"].replace("€", ""))
        for r in rows if r["Category"] == "Electronics"
    )
    other_total_eur = sum(
        float(r["Price (EUR)"].replace("€", ""))
        for r in rows if r["Category"] == "Other"
    )
    total_eur = electronics_total_eur + other_total_eur

    print(f"\nElectronics total: €{electronics_total_eur:.2f}")
    print(f"Other total:       €{other_total_eur:.2f}")
    print(f"Grand total:       €{total_eur:.2f}")

    export_csv(rows)


if __name__ == "__main__":
    main()
