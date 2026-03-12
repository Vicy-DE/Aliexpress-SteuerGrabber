"""AliExpress invoice grabber and order categorizer.

Extracts session cookies from the user's running Firefox browser,
downloads all invoice PDFs from AliExpress completed orders,
categorizes them (electronics vs. other), converts prices to EUR
using ECB historical exchange rates, and outputs a summary CSV.

Receipt data is extracted from the AliExpress Receipt modal iframe
(tax-ui) and converted to PDF with copyable text using fpdf2.
Invoices are organized into year-based subfolders with per-order
markdown files, yearly summaries, and an electronics category folder.
"""

import configparser
import concurrent.futures
import csv
import json
import logging
import math
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv
from fpdf import FPDF
from playwright.sync_api import sync_playwright
from tabulate import tabulate

SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
INVOICES_DIR = SCRIPT_DIR / "invoices"
ANALYSIS_DIR = SCRIPT_DIR / "analysis"
ELECTRONICS_DIR = ANALYSIS_DIR / "electronics"
OUTPUT_CSV = SCRIPT_DIR / "orders_summary.csv"

ALIEXPRESS_ORDER_LIST_URL = "https://www.aliexpress.com/p/order/index.html"
ALIEXPRESS_ORDER_DETAIL_URL = "https://www.aliexpress.com/p/order/detail.html?orderId={order_id}"
ALIEXPRESS_TAX_UI_URL = "https://www.aliexpress.com/p/tax-ui/index.html?isGrayMatch=true&orderId={order_id}"

# Octopart component search URL
OCTOPART_SEARCH_URL = "https://octopart.com/search?q={query}"

# Parallel download workers (headed browser instances)
MAX_WORKERS = 2

# ECB daily exchange rate XML feed (last 90 days)
ECB_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
ECB_NS = {"gesmes": "http://www.gesmes.org/xml/2002-08-01",
           "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}

# Keywords indicating electronic parts or development equipment.
# Matched with word-boundary regex (\b) to avoid false positives
# like "motor" matching "Motorcycle".
ELECTRONICS_KEYWORDS = [
    # PCB / board types (compound to avoid matching "skateboard" etc.)
    "pcb", "circuit board", "dev board", "development board",
    "breakout board", "prototype board",
    # Passive components
    "resistor", "capacitor", "inductor", "diode", "ferrite",
    # Active / semiconductor
    "transistor", "mosfet", "igbt", "ic", "chip", "microcontroller",
    "mcu", "semiconductor", "op-amp", "opamp", "comparator",
    "fpga", "cpld", "eeprom",
    # Dev boards
    "arduino", "esp32", "esp8266", "stm32", "raspberry pi",
    # Sensors & modules
    "sensor", "relay", "gyroscope", "accelerometer",
    # Motors — compound forms only to avoid "motorcycle"
    "servo motor", "stepper motor", "dc motor", "bldc motor",
    "brushless motor", "gear motor", "servo", "stepper",
    "motor driver", "esc", "hyesc",
    # Power
    "transformer", "voltage regulator", "power supply",
    "buck converter", "boost converter", "dc-dc",
    "lipo", "li-ion", "18650",
    # Connectors / wiring
    "dupont", "breadboard", "jumper wire", "pin header",
    "jst connector", "xt60", "xt30",
    # Soldering & tools
    "soldering", "solder", "flux", "multimeter", "oscilloscope",
    "logic analyzer", "programmer", "debugger",
    "voltmeter", "ammeter", "wattmeter", "clamp meter",
    "crimping tool", "ferrule", "shrink tube", "heat shrink",
    # Displays
    "oled", "lcd", "tft",
    # Protocols / interfaces
    "uart", "spi", "i2c",
    # Wireless
    "antenna", "bluetooth module", "wifi module", "lora",
    # Thermal
    "heat sink", "heatsink",
    # Fabrication
    "3d print", "cnc machine", "cnc router", "laser engraver",
    # General electronics terms
    "electronic component", "electronic module", "electronic kit",
    "led strip", "led module", "ws2812", "neopixel",
    "potentiometer", "rotary encoder",
    # Packages
    "smd", "through hole", "dip", "sop", "qfp", "bga",
    # Specific chip references
    "555 timer", "ne555", "lm7805", "lm317",
]

# Keywords that indicate automotive / motorcycle / bicycle parts.
# When present alongside an electronics keyword the item is re-classified
# as "Other" because it is a vehicle part, not a standalone component.
AUTOMOTIVE_KEYWORDS = [
    # Vehicle types
    "motorcycle", "motorbike", "dirt bike", "pit bike",
    "scooter", "atv", "quad",
    # Car diagnostics
    "obd", "obd2", "obdii", "diagnostic",
    "hex v2", "hex-v2", "vag", "inpa", "dcan",
    "enet", "openport", "ecu flash", "j2534",
    "opcom", "elm327",
    # Vehicle-specific parts
    "carburetor", "exhaust", "clutch", "throttle",
    "fuel sensor", "flex fuel", "o2 sensor", "oxygen sensor",
    "lambda", "starter relay", "solenoid",
    "fork", "handlebar", "pedal", "crankset",
    "bottom bracket", "derailleur", "chainring",
    # Vehicle brands / contexts
    "honda", "yamaha", "kawasaki", "suzuki",
    "bmw", "moto guzzi", "buick", "cadillac",
    "lifan", "zongshen", "loncin",
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

    Uses word-boundary regex matching so that e.g. "motor" does not
    match "Motorcycle".  Items that match both an electronics keyword
    and an automotive/vehicle keyword are classified as "Other".

    Args:
        item_titles: List of item title strings from the order.

    Returns:
        "Electronics" if any item matches electronics keywords
        without matching automotive exclusions, else "Other".
    """
    combined = " ".join(item_titles).lower()

    # Check for automotive / vehicle context first
    is_automotive = False
    for keyword in AUTOMOTIVE_KEYWORDS:
        pattern = r"\b" + re.escape(keyword.strip()) + r"\b"
        if re.search(pattern, combined):
            is_automotive = True
            break

    for keyword in ELECTRONICS_KEYWORDS:
        pattern = r"\b" + re.escape(keyword.strip()) + r"\b"
        if re.search(pattern, combined):
            if is_automotive:
                # Vehicle part that happens to mention an electronics term
                continue
            return "Electronics"
    return "Other"


def find_firefox_profile():
    """Find the default Firefox profile directory on Windows.

    Returns:
        Path to the Firefox profile directory.

    Raises:
        FileNotFoundError: If no Firefox profile is found.
    """
    # Search for profiles.ini in standard and MSIX Store app locations
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")

    candidates = [
        Path(appdata) / "Mozilla" / "Firefox" / "profiles.ini",
    ]

    # MSIX / Microsoft Store Firefox: profiles live under LocalCache
    packages_dir = Path(localappdata) / "Packages"
    if packages_dir.exists():
        for pkg in packages_dir.iterdir():
            if pkg.name.startswith("Mozilla.Firefox"):
                msix_ini = pkg / "LocalCache" / "Roaming" / "Mozilla" / "Firefox" / "profiles.ini"
                candidates.insert(0, msix_ini)  # prefer Store app if present

    profiles_ini = None
    for candidate in candidates:
        if candidate.exists():
            profiles_ini = candidate
            break

    if profiles_ini is None:
        raise FileNotFoundError(
            "Firefox profiles.ini not found. Searched:\n"
            + "\n".join(f"  - {c}" for c in candidates)
            + "\nIs Firefox installed?"
        )

    firefox_dir = profiles_ini.parent
    print(f"Found profiles.ini: {profiles_ini}")

    config = configparser.ConfigParser()
    config.read(str(profiles_ini))

    # Priority 1: InstallXXX section's Default= key (the actively used profile)
    profile_path = None
    for section in config.sections():
        if section.startswith("Install"):
            path = config.get(section, "Default", fallback="")
            if path:
                candidate = firefox_dir / path
                if candidate.exists() and (candidate / "cookies.sqlite").exists():
                    profile_path = candidate
                    break

    # Priority 2: Profile sections — prefer one with cookies.sqlite
    if profile_path is None:
        fallback = None
        for section in config.sections():
            if not section.startswith("Profile"):
                continue
            is_relative = config.get(section, "IsRelative", fallback="1") == "1"
            path = config.get(section, "Path", fallback="")

            if path:
                candidate = (firefox_dir / path) if is_relative else Path(path)
                if candidate.exists() and (candidate / "cookies.sqlite").exists():
                    profile_path = candidate
                    break
                if fallback is None and candidate.exists():
                    fallback = candidate

        if profile_path is None:
            profile_path = fallback

    if profile_path is None or not profile_path.exists():
        raise FileNotFoundError(
            "Could not find a Firefox profile directory. "
            "Make sure Firefox is installed and has been used at least once."
        )

    print(f"Found Firefox profile: {profile_path}")
    return profile_path


def extract_firefox_cookies(profile_path, domain_filter=".aliexpress.com"):
    """Extract cookies from a running Firefox instance's profile.

    Copies the cookies database to a temp file to avoid locking conflicts
    with the running Firefox process.

    Args:
        profile_path: Path to the Firefox profile directory.
        domain_filter: Domain to filter cookies for.

    Returns:
        List of cookie dicts compatible with Playwright's add_cookies().
    """
    cookies_db = profile_path / "cookies.sqlite"
    if not cookies_db.exists():
        raise FileNotFoundError(f"cookies.sqlite not found in {profile_path}")

    # Copy the database files to a temp location (Firefox holds a lock)
    tmp_dir = tempfile.mkdtemp(prefix="firefox_cookies_")
    tmp_db = Path(tmp_dir) / "cookies.sqlite"
    shutil.copy2(str(cookies_db), str(tmp_db))

    # Also copy WAL and SHM files if they exist (for recent writes)
    for suffix in ["-wal", "-shm"]:
        wal_file = profile_path / f"cookies.sqlite{suffix}"
        if wal_file.exists():
            shutil.copy2(str(wal_file), str(Path(tmp_dir) / f"cookies.sqlite{suffix}"))

    cookies = []
    try:
        conn = sqlite3.connect(str(tmp_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT host, name, value, path, expiry, isSecure, isHttpOnly, sameSite "
            "FROM moz_cookies WHERE host LIKE ?",
            (f"%{domain_filter}%",)
        )

        sameSite_map = {0: "None", 1: "Lax", 2: "Strict"}

        for row in cursor.fetchall():
            host, name, value, path, expiry, is_secure, is_http_only, same_site = row
            cookie = {
                "name": name,
                "value": value,
                "domain": host,
                "path": path or "/",
                "secure": bool(is_secure),
                "httpOnly": bool(is_http_only),
                "sameSite": sameSite_map.get(same_site, "None"),
            }
            if expiry and expiry > 0:
                # Firefox MSIX stores expiry in milliseconds — convert to seconds
                if expiry > 1e12:
                    expiry = int(expiry / 1000)
                cookie["expires"] = expiry
            else:
                cookie["expires"] = -1  # session cookie
            cookies.append(cookie)

        conn.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"  Extracted {len(cookies)} AliExpress cookies from Firefox.")
    if not cookies:
        print("  WARNING: No AliExpress cookies found!")
        print("  Make sure you are logged into AliExpress in Firefox.")
    return cookies


def scrape_order_list(page):
    """Scrape all orders from the AliExpress order list pages via DOM.

    Uses JavaScript evaluation with the actual AliExpress CSS class structure
    (order-item containers with sub-classes for header, content, price, etc.).

    Args:
        page: Playwright page on the order list.

    Returns:
        List of order dicts with keys: order_id, date, items, total_usd.
    """
    orders = []
    seen_ids = set()
    max_scroll_attempts = 200
    stale_rounds = 0
    max_stale_rounds = 5

    # Wait for order items to appear
    try:
        page.wait_for_selector(".order-item", timeout=15000)
    except Exception:
        print("  No .order-item elements found on page.")
        return orders

    for attempt in range(max_scroll_attempts):
        page_orders = page.evaluate("""() => {
            const orders = [];
            const cards = document.querySelectorAll('.order-item');
            cards.forEach(card => {
                // Order ID — look in header-right-info area
                const idEl = card.querySelector(
                    '.order-item-header-right-info, [class*="order-item-header-right"]'
                );
                let orderId = '';
                if (idEl) {
                    const idMatch = idEl.textContent.match(/\\d{10,}/);
                    if (idMatch) orderId = idMatch[0];
                }

                // Date — header text containing "Order date:"
                const headerEl = card.querySelector('.order-item-header');
                let dateStr = '';
                if (headerEl) {
                    const dateMatch = headerEl.textContent.match(
                        /Order date:\\s*([A-Za-z]+ \\d{1,2},\\s*\\d{4})/
                    );
                    if (dateMatch) dateStr = dateMatch[1];
                }

                // Product names
                const items = [];
                card.querySelectorAll('.order-item-content-info-name').forEach(el => {
                    const txt = el.textContent.trim();
                    if (txt) items.push(txt);
                });

                // Total price
                const priceEl = card.querySelector(
                    '.order-item-content-opt-price-total'
                );
                let totalText = '';
                if (priceEl) {
                    totalText = priceEl.textContent.trim();
                }

                if (orderId) {
                    orders.push({
                        order_id: orderId,
                        date: dateStr,
                        total_text: totalText,
                        items: items
                    });
                }
            });
            return orders;
        }""")

        new_count = 0
        for o in page_orders:
            if o["order_id"] not in seen_ids:
                seen_ids.add(o["order_id"])
                order = parse_raw_order(o)
                if order and order["order_id"]:
                    orders.append(order)
                    new_count += 1

        print(f"  Scroll {attempt + 1}: {len(orders)} orders total (+{new_count} new)")

        if new_count == 0:
            stale_rounds += 1
            if stale_rounds >= max_stale_rounds:
                print(f"  No new orders for {max_stale_rounds} rounds, stopping.")
                break
        else:
            stale_rounds = 0

        # Scroll to bottom to trigger lazy loading
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

        # Click "View orders" button to load next batch (try multiple selectors)
        has_more = page.evaluate("""() => {
            // Try the standard button first
            let btn = document.querySelector('.order-more button');
            if (btn && btn.offsetParent !== null) {
                btn.click();
                return true;
            }
            // Try alternative selectors
            const candidates = document.querySelectorAll(
                'button, [class*="load-more"], [class*="view-more"], [class*="order-more"]'
            );
            for (const el of candidates) {
                const text = el.textContent.trim().toLowerCase();
                if (text.includes('view') && text.includes('order')) {
                    el.click();
                    return true;
                }
            }
            return false;
        }""")
        if has_more:
            time.sleep(3)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
        else:
            # No more "View orders" button — all orders loaded
            break

    print(f"  Scraping complete: {len(orders)} orders found.")
    return orders


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


def extract_receipt_data(page, order_id):
    """Extract structured receipt data from the AliExpress tax-ui page.

    Navigates directly to the tax-ui receipt URL for the given order,
    waits for the page to render, and scrapes structured data from the DOM.

    Args:
        page: Playwright page object.
        order_id: AliExpress order ID string.

    Returns:
        Dict with receipt data, or None if extraction failed.
    """
    tax_url = ALIEXPRESS_TAX_UI_URL.format(order_id=order_id)
    try:
        page.goto(tax_url)
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception as exc:
        print(f"    tax-ui page failed to load: {exc}")
        return None
    time.sleep(3)

    # Wait for receipt content to render (React hydration)
    has_content = False
    for attempt in range(15):
        has_content = page.evaluate("""
            () => document.querySelectorAll('[class*="summary--row"]').length > 0
        """)
        if has_content:
            break
        time.sleep(1)

    if not has_content:
        print("    tax-ui page has no receipt content.")
        return None

    # Extract structured data from the page DOM
    data = page.evaluate("""() => {
        const result = {
            order_id: '', order_time: '', items: [],
            subtotal: '', discount: '', shipping: '', total: '', vat: '',
            address_lines: [], payment_method: ''
        };

        // Summary rows — actual classes are summary--left/summary--right
        const rows = document.querySelectorAll('[class*="summary--row"]');
        rows.forEach(row => {
            const label = row.querySelector('[class*="summary--left"]');
            const value = row.querySelector('[class*="summary--right"]');
            if (!label || !value) return;
            const l = label.textContent.trim().toLowerCase();
            const v = value.textContent.trim();
            if (l.includes('order id') || l.includes('order number')) result.order_id = v;
            else if (l.includes('order time') || l.includes('date')) result.order_time = v;
            else if (l.includes('subtotal')) result.subtotal = v;
            else if (l.includes('discount')) result.discount = v;
            else if (l.includes('shipping')) result.shipping = v;
            else if (l.includes('vat') || l.includes('tax')) result.vat = v;
            else if (l.includes('total') && !l.includes('sub')) result.total = v;
        });

        // Product items — actual class is products--product
        const products = document.querySelectorAll('[class*="products--product--"]');
        products.forEach(product => {
            const titleEl = product.querySelector('[class*="product-title"]');
            const priceEl = product.querySelector('[class*="product-price"]');
            const skuEl = product.querySelector('[class*="product-sku"]');
            result.items.push({
                title: titleEl ? titleEl.textContent.trim() : '',
                price: priceEl ? priceEl.textContent.trim() : '',
                sku: skuEl ? skuEl.textContent.trim() : '',
                quantity: '1',
            });
        });

        // If no products found via class, try products container text
        if (result.items.length === 0) {
            const prodContainer = document.querySelector('[class*="products--container"]');
            if (prodContainer) {
                const text = prodContainer.innerText.trim();
                if (text) result.items.push({title: text, price: '', sku: '', quantity: '1'});
            }
        }

        // Shipping address
        const addrContainer = document.querySelector('[class*="address--container"]');
        if (addrContainer) {
            result.address_lines = addrContainer.innerText.trim().split('\\n').filter(l => l.trim());
        }

        // Payment method
        const payContainer = document.querySelector('[class*="payment--container"]');
        if (payContainer) {
            result.payment_method = payContainer.innerText.trim();
        }

        return result;
    }""")

    return data


def convert_png_to_pdf(png_path, pdf_path):
    """Convert a PNG screenshot to a single-page PDF.

    Embeds the full screenshot image into an A4-width PDF page,
    scaling the height proportionally so the entire screenshot is visible.

    Args:
        png_path: Path to the source PNG file.
        pdf_path: Path where the resulting PDF will be saved.

    Returns:
        Path to the created PDF, or None on failure.
    """
    try:
        from PIL import Image

        with Image.open(str(png_path)) as img:
            img_w, img_h = img.size

        pdf = FPDF()
        # A4 width = 210 mm, use 190 mm with 10 mm margins
        page_w = 190
        scale = page_w / img_w
        page_h = img_h * scale
        pdf.add_page(format=(page_w + 20, page_h + 20))
        pdf.image(str(png_path), x=10, y=10, w=page_w)

        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(str(pdf_path))
        return pdf_path
    except Exception as exc:
        print(f"    PNG→PDF conversion failed: {exc}")
        return None


def generate_invoice_pdf(receipt_data, pdf_path):
    """Generate a PDF invoice with copyable text from receipt data.

    Args:
        receipt_data: Dict with structured receipt data from extract_receipt_data().
        pdf_path: Path where to save the PDF.
    """
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # Sanitize text for PDF (Helvetica doesn't support all Unicode)
    replacements = {"€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR",
                    "…": "...", "\u2013": "-", "\u2014": "--",
                    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}

    def safe(text):
        for char, repl in replacements.items():
            text = text.replace(char, repl)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "AliExpress Order Receipt", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(8)

    # Order info
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Order Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    info_fields = [
        ("Order ID", receipt_data.get("order_id", "")),
        ("Order Time", receipt_data.get("order_time", "")),
    ]
    for label, value in info_fields:
        if value:
            pdf.cell(40, 6, f"{label}:", new_x="RIGHT")
            pdf.cell(0, 6, safe(value), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Items table
    items = receipt_data.get("items", [])
    if items:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Items", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(110, 6, "Product", border=1)
        pdf.cell(25, 6, "Qty", border=1, align="C")
        pdf.cell(40, 6, "Price", border=1, align="R")
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for item in items:
            title = item.get("title", "")
            # Truncate long titles to fit
            if len(title) > 65:
                title = title[:62] + "..."
            pdf.cell(110, 6, safe(title), border=1)
            pdf.cell(25, 6, str(item.get("quantity", "1")), border=1, align="C")
            pdf.cell(40, 6, safe(item.get("price", "")), border=1, align="R")
            pdf.ln()
        pdf.ln(4)

    # Financial summary
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Payment Details", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    price_fields = [
        ("Subtotal", receipt_data.get("subtotal", "")),
        ("Discount", receipt_data.get("discount", "")),
        ("Shipping", receipt_data.get("shipping", "")),
        ("VAT", receipt_data.get("vat", "")),
    ]
    for label, value in price_fields:
        if value:
            pdf.cell(40, 6, f"{label}:", new_x="RIGHT")
            pdf.cell(0, 6, safe(value), new_x="LMARGIN", new_y="NEXT")

    total = receipt_data.get("total", "")
    if total:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(40, 7, "Total:", new_x="RIGHT")
        pdf.cell(0, 7, safe(total), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Shipping address
    address_lines = receipt_data.get("address_lines", [])
    if address_lines:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Shipping Address", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for line in address_lines:
            if line.strip():
                pdf.cell(0, 6, safe(line.strip()), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Payment method
    payment = receipt_data.get("payment_method", "")
    if payment:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Payment Method", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for line in payment.split("\n"):
            if line.strip():
                pdf.cell(0, 6, safe(line.strip()), new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(pdf_path))


def generate_invoice_md(receipt_data, order, md_path, ecb_rates):
    """Generate a Markdown invoice file for a single order.

    Args:
        receipt_data: Dict with structured receipt data.
        order: Order dict with date, items, total_usd, category, etc.
        md_path: Path where to save the .md file.
        ecb_rates: ECB exchange rate dict.
    """
    md_path.parent.mkdir(parents=True, exist_ok=True)

    eur_amount, rate, rate_date = usd_to_eur_rounded_up(
        order["total_usd"], order["date"], ecb_rates
    )

    lines = [
        f"# Invoice — Order {order['order_id']}",
        "",
        f"**Date:** {order['date']}",
        f"**Order ID:** {order['order_id']}",
        f"**Category:** {order.get('category', 'Other')}",
        "",
        "## Items",
        "",
        "| Product | Qty | Price |",
        "|---------|-----|-------|",
    ]

    items = receipt_data.get("items", []) if receipt_data else []
    if items:
        for item in items:
            title = item.get("title", "N/A").replace("|", "/")
            qty = item.get("quantity", "1")
            price = item.get("price", "")
            lines.append(f"| {title} | {qty} | {price} |")
    else:
        for title in order.get("items", []):
            lines.append(f"| {title.replace('|', '/')} | 1 | — |")

    lines += [
        "",
        "## Financial Summary",
        "",
    ]

    if receipt_data:
        for label, key in [("Subtotal", "subtotal"), ("Discount", "discount"),
                           ("Shipping", "shipping"), ("VAT", "vat"), ("Total", "total")]:
            val = receipt_data.get(key, "")
            if val:
                lines.append(f"- **{label}:** {val}")
    else:
        lines.append(f"- **Total (USD):** ${order['total_usd']:.2f}")

    lines += [
        "",
        "## EUR Conversion",
        "",
        f"- **Price (EUR):** €{eur_amount:.2f}",
        f"- **Exchange Rate:** {rate:.4f} USD/EUR (date: {rate_date})",
        "",
    ]

    if receipt_data:
        address = receipt_data.get("address_lines", [])
        if address:
            lines += ["## Shipping Address", ""]
            for line in address:
                if line.strip():
                    lines.append(line.strip())
            lines.append("")

        payment = receipt_data.get("payment_method", "")
        if payment:
            lines += ["## Payment Method", ""]
            for line in payment.split("\n"):
                if line.strip():
                    lines.append(line.strip())
            lines.append("")

    # Octopart part identification for electronics orders
    if order.get("category") == "Electronics":
        item_titles = []
        if receipt_data and receipt_data.get("items"):
            item_titles = [i.get("title", "") for i in receipt_data["items"] if i.get("title")]
        elif order.get("items"):
            item_titles = order["items"]
        if item_titles:
            lines += ["## Component Identification", ""]
            for title in item_titles:
                parts = extract_part_numbers(title)
                if parts:
                    url = octopart_search_url(parts[0])
                    lines.append(f"- **{', '.join(parts)}** — {title} ([Octopart]({url}))")
                else:
                    url = octopart_search_url(title[:40])
                    lines.append(f"- {title} ([Octopart]({url}))")
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")


def download_invoice_from_detail_page(page, order, ecb_rates):
    """Extract receipt data from current page and generate PDF + MD.

    The page must already be on the order detail page.
    Uses the Receipt modal iframe to extract structured data, then generates
    a PDF with copyable text and a companion Markdown invoice file.
    Files are saved into year-based subfolders.

    Args:
        page: Playwright page object (already on order detail page).
        order: Order dict with order_id, date, items, total_usd, category.
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

    if pdf_path.exists():
        print(f"  Invoice {filename_base}.pdf already exists, skipping.")
        return pdf_path

    # Extract receipt data by navigating directly to the tax-ui page
    receipt_data = extract_receipt_data(page, order_id)

    if receipt_data:
        # Generate PDF with copyable text
        generate_invoice_pdf(receipt_data, pdf_path)
        print(f"  Generated PDF invoice: {filename_base}.pdf")

        # Generate companion Markdown file
        generate_invoice_md(receipt_data, order, md_path, ecb_rates)
        print(f"  Generated MD invoice:  {filename_base}.md")
        return pdf_path

    # Fallback: re-navigate to the detail page for a clean screenshot
    png_path = year_dir / f"{filename_base}.png"
    if png_path.exists():
        # Convert existing PNG to PDF if not already done
        converted = convert_png_to_pdf(png_path, pdf_path)
        if converted:
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
        # Convert screenshot to PDF
        convert_png_to_pdf(png_path, pdf_path)
        generate_invoice_md(None, order, md_path, ecb_rates)
        print(f"  Saved screenshot+PDF for order {order_id}")
        return pdf_path
    except Exception as e:
        print(f"  Could not save screenshot for order {order_id}: {e}")
        return None


def enrich_and_download(page, order, ecb_rates):
    """Navigate to order detail once, enrich missing data, and download invoice.

    Combines enrichment and receipt extraction in a single page navigation
    to avoid the Receipt button disappearing on re-navigation.

    Args:
        page: Playwright page object.
        order: Order dict.
        ecb_rates: ECB exchange rate dict.

    Returns:
        Tuple of (updated_order, pdf_path_or_None).
    """
    detail_url = ALIEXPRESS_ORDER_DETAIL_URL.format(order_id=order["order_id"])
    page.goto(detail_url)
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Enrich missing fields from the detail page
    if not order["total_usd"] or not order["items"] or not order["date"]:
        detail = page.evaluate("""() => {
            const result = {items: [], total_text: '', date: ''};
            document.querySelectorAll(
                '.order-item-content-info-name, [class*="product-title"], [class*="item-title"]'
            ).forEach(el => result.items.push(el.textContent.trim()));
            const priceEl = document.querySelector(
                '.order-item-content-opt-price-total, [class*="total-price"], [class*="order-amount"]'
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
                    '[class*="order-time"], [class*="order-date"], [class*="pay-time"]'
                );
                if (dateEl) result.date = dateEl.textContent.trim();
            }
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

        # Re-categorize after enrichment
        order["category"] = categorize_order(order["items"])

    # Download invoice (page is already on the detail page)
    pdf_path = download_invoice_from_detail_page(page, order, ecb_rates)

    return order, pdf_path


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

        // Item titles — use the actual AliExpress CSS classes
        document.querySelectorAll(
            '.order-item-content-info-name, [class*="product-title"], [class*="item-title"]'
        ).forEach(el => result.items.push(el.textContent.trim()));

        // Total price
        const priceEl = document.querySelector(
            '.order-item-content-opt-price-total, [class*="total-price"], [class*="order-amount"]'
        );
        if (priceEl) result.total_text = priceEl.textContent.trim();

        // Date
        const headerEl = document.querySelector('.order-item-header');
        if (headerEl) {
            const dateMatch = headerEl.textContent.match(
                /Order date:\\s*([A-Za-z]+ \\d{1,2},\\s*\\d{4})/
            );
            if (dateMatch) result.date = dateMatch[1];
        }
        if (!result.date) {
            const dateEl = document.querySelector(
                '[class*="order-time"], [class*="order-date"], [class*="pay-time"]'
            );
            if (dateEl) result.date = dateEl.textContent.trim();
        }

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
    """Scrape orders by intercepting AliExpress MTOP API (JSONP) responses.

    The AliExpress order list page uses the MTOP API endpoint
    ``mtop.aliexpress.trade.buyer.order.list`` which returns JSONP. This
    function strips the callback wrapper and parses the JSON payload.

    Args:
        page: Playwright page object.

    Returns:
        List of order dicts, or empty list if API interception fails.
    """
    orders = []
    api_responses = []

    def handle_response(response):
        url = response.url
        if "mtop.aliexpress.trade.buyer.order" in url.lower():
            try:
                body = response.text()
                # Strip JSONP callback wrapper: mtopjsonpN({...})
                match = re.search(r"mtopjsonp\d+\((.+)\)\s*;?\s*$", body, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    api_responses.append(data)
                else:
                    # Try plain JSON
                    data = json.loads(body)
                    api_responses.append(data)
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
            # Navigate the MTOP response structure: data -> orderList
            if isinstance(resp_body, dict):
                data = resp_body.get("data", {})
                if isinstance(data, dict):
                    order_list = data.get("orderList", data.get("orders", data.get("list")))
                    if not order_list:
                        # Try nested result
                        result = data.get("result", data.get("body", {}))
                        if isinstance(result, dict):
                            order_list = result.get("orderList", result.get("orders"))
                        elif isinstance(result, list):
                            order_list = result

            if not order_list or not isinstance(order_list, list):
                continue

            for api_order in order_list:
                if not isinstance(api_order, dict):
                    continue
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
                            if isinstance(item, dict):
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


def generate_yearly_summary(year, year_orders, ecb_rates, output_dir):
    """Generate a yearly summary Markdown file.

    Args:
        year: Year string (e.g. "2025").
        year_orders: List of order dicts for this year.
        ecb_rates: ECB exchange rate dict.
        output_dir: Directory to save the summary file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / f"{year}_summary.md"

    total_usd = sum(o["total_usd"] for o in year_orders)
    electronics_orders = [o for o in year_orders if o.get("category") == "Electronics"]
    other_orders = [o for o in year_orders if o.get("category") != "Electronics"]

    electronics_usd = sum(o["total_usd"] for o in electronics_orders)
    other_usd = sum(o["total_usd"] for o in other_orders)

    lines = [
        f"# Yearly Summary — {year}",
        "",
        f"**Total Orders:** {len(year_orders)}",
        f"**Electronics Orders:** {len(electronics_orders)}",
        f"**Other Orders:** {len(other_orders)}",
        "",
        "## All Orders",
        "",
        "| Date | Order ID | Items | Category | USD | EUR |",
        "|------|----------|-------|----------|-----|-----|",
    ]

    total_eur = 0.0
    electronics_eur = 0.0
    other_eur = 0.0

    for o in sorted(year_orders, key=lambda x: x["date"]):
        eur, _, _ = usd_to_eur_rounded_up(o["total_usd"], o["date"], ecb_rates)
        total_eur += eur
        if o.get("category") == "Electronics":
            electronics_eur += eur
        else:
            other_eur += eur
        items_str = "; ".join(o["items"])[:60].replace("|", "/") if o["items"] else "(no title)"
        cat = o.get("category", "Other")
        lines.append(f"| {o['date']} | {o['order_id']} | {items_str} | {cat} | ${o['total_usd']:.2f} | €{eur:.2f} |")

    lines += [
        "",
        "## Totals",
        "",
        f"| Category | USD | EUR |",
        f"|----------|-----|-----|",
        f"| Electronics | ${electronics_usd:.2f} | €{electronics_eur:.2f} |",
        f"| Other | ${other_usd:.2f} | €{other_eur:.2f} |",
        f"| **Grand Total** | **${total_usd:.2f}** | **€{total_eur:.2f}** |",
        "",
    ]

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Yearly summary saved: {summary_path.name}")


def generate_order_summary(orders, ecb_rates, output_path):
    """Generate an overall order summary Markdown file.

    Args:
        orders: List of all order dicts.
        ecb_rates: ECB exchange rate dict.
        output_path: Path to save the summary file.
    """
    total_usd = sum(o["total_usd"] for o in orders)
    electronics_orders = [o for o in orders if o.get("category") == "Electronics"]
    other_orders = [o for o in orders if o.get("category") != "Electronics"]

    lines = [
        "# AliExpress Order Summary",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Total Orders:** {len(orders)}",
        f"**Electronics:** {len(electronics_orders)}",
        f"**Other:** {len(other_orders)}",
        "",
        "## All Orders",
        "",
        "| # | Date | Order ID | Items | Category | USD | EUR |",
        "|---|------|----------|-------|----------|-----|-----|",
    ]

    grand_eur = 0.0
    for i, o in enumerate(sorted(orders, key=lambda x: x["date"]), 1):
        eur, _, _ = usd_to_eur_rounded_up(o["total_usd"], o["date"], ecb_rates)
        grand_eur += eur
        items_str = "; ".join(o["items"])[:55].replace("|", "/") if o["items"] else "(no title)"
        cat = o.get("category", "Other")
        lines.append(f"| {i} | {o['date']} | {o['order_id']} | {items_str} | {cat} | ${o['total_usd']:.2f} | €{eur:.2f} |")

    lines += [
        "",
        "## Summary by Year",
        "",
    ]

    years = sorted(set(o["date"][:4] for o in orders if len(o["date"]) >= 4))
    for year in years:
        yo = [o for o in orders if o["date"].startswith(year)]
        y_usd = sum(o["total_usd"] for o in yo)
        y_eur = sum(usd_to_eur_rounded_up(o["total_usd"], o["date"], ecb_rates)[0] for o in yo)
        lines.append(f"- **{year}:** {len(yo)} orders — ${y_usd:.2f} / €{y_eur:.2f}")

    lines += [
        "",
        "## Totals",
        "",
        f"- **Total (USD):** ${total_usd:.2f}",
        f"- **Total (EUR):** €{grand_eur:.2f}",
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Order summary saved: {output_path}")


def copy_electronics_invoices(orders, electronics_dir):
    """Copy electronics order invoices to a dedicated folder.

    Args:
        orders: List of all order dicts.
        electronics_dir: Path to the electronics folder.
    """
    electronics_dir.mkdir(parents=True, exist_ok=True)

    electronics_orders = [o for o in orders if o.get("category") == "Electronics"]
    if not electronics_orders:
        return

    count = 0
    for order in electronics_orders:
        date_str = order.get("date", "unknown")
        year = date_str[:4] if len(date_str) >= 4 else "unknown"
        filename_base = f"{date_str}-{order['order_id']}"
        source_dir = INVOICES_DIR / year

        for ext in [".pdf", ".md", ".png"]:
            src = source_dir / f"{filename_base}{ext}"
            if src.exists():
                dst = electronics_dir / f"{filename_base}{ext}"
                shutil.copy2(str(src), str(dst))
                count += 1

    print(f"  Copied {count} files for {len(electronics_orders)} electronics orders.")


def octopart_search_url(query):
    """Generate an Octopart search URL for a component query.

    Args:
        query: Component name or description to search for.

    Returns:
        Octopart search URL string.
    """
    return OCTOPART_SEARCH_URL.format(query=quote_plus(query))


def extract_part_numbers(title):
    """Extract likely electronic component part numbers from a product title.

    Looks for common part number patterns (chip families, passives,
    connectors, etc.) and returns a list of matches.

    Args:
        title: Product title string.

    Returns:
        List of extracted part number strings.
    """
    patterns = [
        # Chip families — e.g. ESP32, STM32F429, ATmega2560, PIC16F877
        r"\b(ESP32[A-Z0-9-]*)\b",
        r"\b(ESP8266[A-Z0-9-]*)\b",
        r"\b(STM32[A-Z0-9]+)\b",
        r"\b(ATmega[0-9A-Z]+)\b",
        r"\b(AT[0-9]{2}[A-Z][0-9A-Z]+)\b",
        r"\b(PIC[0-9]+[A-Z0-9]*)\b",
        r"\b(CH32[A-Z0-9]+)\b",
        r"\b(RP2040)\b",
        # Discrete semiconductors — e.g. 1N4007, 2N2222, BC547
        r"\b([12]N[0-9]{3,5}[A-Z]?)\b",
        r"\b(BC[0-9]{3}[A-Z]?)\b",
        r"\b(IRF[0-9]+[A-Z]*)\b",
        # ICs — e.g. NE555, LM7805, LM317, SN65HVD230, 74HC595
        r"\b(NE555[A-Z]*)\b",
        r"\b(LM[0-9]{3,5}[A-Z]*)\b",
        r"\b(SN[0-9]+[A-Z0-9]+)\b",
        r"\b(74[HCL][A-Z]*[0-9]+)\b",
        r"\b(ULN200[0-9])\b",
        # Connectors — e.g. JST-XH, XT60, XT30
        r"\b(JST-?[A-Z]+)\b",
        r"\b(XT[0-9]{2})\b",
        # Displays — e.g. SSD1306, ILI9341
        r"\b(SSD[0-9]{4})\b",
        r"\b(ILI[0-9]{4})\b",
        r"\b(ST77[0-9]{2})\b",
        # Wireless — e.g. NRF24L01, CC2530
        r"\b(NRF[0-9A-Z]+)\b",
        r"\b(CC[0-9]{4})\b",
        # Sensors — e.g. MPU6050, BMP280, DHT11
        r"\b(MPU[0-9]+)\b",
        r"\b(BMP[0-9]+)\b",
        r"\b(DHT[0-9]+)\b",
        r"\b(ACS[0-9]+)\b",
        # Packages with part refs — e.g. MEGA2560, A2212
        r"\b(MEGA[0-9]+)\b",
        r"\b(A22[0-9]{2})\b",
        # LED chips — e.g. WS2812, SK6812
        r"\b(WS28[0-9]+[A-Z]*)\b",
        r"\b(SK68[0-9]+)\b",
        # Modules — e.g. PCF8574, ADS1115
        r"\b(PCF[0-9]{4}[A-Z]*)\b",
        r"\b(ADS[0-9]{4})\b",
        r"\b(MCP[0-9]{4})\b",
        # Motor drivers — e.g. L298N, A4988, TMC2209
        r"\b(L298[A-Z]?)\b",
        r"\b(A4988)\b",
        r"\b(TMC[0-9]{4})\b",
        r"\b(DRV[0-9]+)\b",
        # Power — e.g. LM2596, XL6009
        r"\b(LM25[0-9]{2})\b",
        r"\b(XL[0-9]{4})\b",
        # WiFi/BT modules — e.g. QCNFA435, QCA9377
        r"\b(QC[A-Z]*[0-9]{3,})\b",
    ]
    parts = []
    for pat in patterns:
        for match in re.finditer(pat, title, re.IGNORECASE):
            part = match.group(1).upper()
            if part not in parts:
                parts.append(part)
    return parts


def generate_octopart_report(orders, output_path):
    """Generate a Markdown report with extracted part numbers for electronics items.

    Lists electronics order items with extracted component part numbers
    and Octopart search URLs for verification.

    Args:
        orders: List of all order dicts.
        output_path: Path to save the report file.
    """
    electronics_orders = [o for o in orders if o.get("category") == "Electronics"]
    if not electronics_orders:
        return

    lines = [
        "# Electronics Components — Part Identification",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Electronics Orders:** {len(electronics_orders)}",
        "",
        "| Date | Order ID | Item | Part Number(s) | Octopart |",
        "|------|----------|------|----------------|----------|",
    ]

    for order in sorted(electronics_orders, key=lambda x: x["date"]):
        if order["items"]:
            for item in order["items"]:
                parts = extract_part_numbers(item)
                parts_str = ", ".join(parts) if parts else "—"
                search_q = parts[0] if parts else item[:40]
                url = octopart_search_url(search_q)
                title = item[:60].replace("|", "/")
                lines.append(
                    f"| {order['date']} | {order['order_id']} | "
                    f"{title} | {parts_str} | [Search]({url}) |"
                )
        else:
            lines.append(
                f"| {order['date']} | {order['order_id']} | "
                f"*(no title)* | — | — |"
            )

    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Octopart report saved: {output_path}")


def generate_run_report(orders, download_paths, ecb_rates):
    """Generate a comprehensive Markdown run report of all orders.

    Groups orders by year and shows download status (PDF / Screenshot / Failed).
    Includes totals per year in USD and EUR, plus a failed downloads section.

    Args:
        orders: List of order dicts.
        download_paths: Dict mapping order_id to Path (or None for failures).
        ecb_rates: ECB exchange rate dict for EUR conversion.
    """
    report_path = SCRIPT_DIR / "run_report.md"
    lines = ["# AliExpress Invoice Grabber — Run Report", ""]
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    pdf_count = sum(
        1 for p in download_paths.values()
        if p and str(p).endswith(".pdf")
    )
    png_count = sum(
        1 for p in download_paths.values()
        if p and str(p).endswith(".png")
    )
    fail_count = sum(1 for p in download_paths.values() if not p)

    lines.append(f"**Total Orders:** {len(orders)}")
    lines.append(f"**PDF Invoices:** {pdf_count}")
    lines.append(f"**Screenshot Fallbacks:** {png_count}")
    lines.append(f"**Failed Downloads:** {fail_count}")
    lines.append("")

    # Group by year
    by_year = {}
    for order in orders:
        year = order["date"][:4] if len(order["date"]) >= 4 else "unknown"
        by_year.setdefault(year, []).append(order)

    for year in sorted(by_year.keys()):
        year_orders = by_year[year]
        lines.append(f"## {year} ({len(year_orders)} orders)")
        lines.append("")
        lines.append("| # | Date | Order ID | Items | USD | Status |")
        lines.append("|---|------|----------|-------|-----|--------|")

        year_total_usd = 0.0
        for i, order in enumerate(sorted(year_orders, key=lambda o: o["date"]), 1):
            oid = order["order_id"]
            path = download_paths.get(oid)
            if path and str(path).endswith(".pdf"):
                status = "✓ PDF"
            elif path and str(path).endswith(".png"):
                status = "📷 Screenshot"
            else:
                status = "✗ Failed"
            items_str = "; ".join(order["items"][:2])
            if len(order["items"]) > 2:
                items_str += f" (+{len(order['items']) - 2})"
            year_total_usd += order["total_usd"]
            lines.append(
                f"| {i} | {order['date']} | {oid} | "
                f"{items_str[:60]} | ${order['total_usd']:.2f} | {status} |"
            )

        rate = ecb_rates.get(year + "-01-01")
        if rate:
            year_total_eur = math.ceil(year_total_usd / rate * 100) / 100
            lines.append(f"\n**Year total:** ${year_total_usd:.2f} ≈ €{year_total_eur:.2f}")
        else:
            lines.append(f"\n**Year total:** ${year_total_usd:.2f}")
        lines.append("")

    # Failed downloads section
    failed = [o for o in orders if not download_paths.get(o["order_id"])]
    if failed:
        lines.append("## Failed Downloads")
        lines.append("")
        for order in failed:
            lines.append(f"- **{order['order_id']}** ({order['date']}): "
                         f"{'; '.join(order['items'][:2])}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRun report saved: {report_path}")


def _process_order_batch(batch_args):
    """Process a batch of orders in a dedicated Playwright browser instance.

    Each worker launches its own headed Firefox with injected cookies,
    processes its assigned orders, and returns the results. Orders from 2026
    are retried once on failure with a fresh browser context.

    Args:
        batch_args: Tuple of (orders_batch, firefox_cookies, ecb_rates, worker_id).

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
                order, pdf_path = enrich_and_download(page, order, ecb_rates)
                if pdf_path and str(pdf_path).endswith(".pdf"):
                    results.append((order, pdf_path))
                    logging.info("[W%d] ✓ Order %s (PDF)", worker_id, order['order_id'])
                elif pdf_path:
                    results.append((order, pdf_path))
                    logging.info("[W%d] 📷 Order %s (screenshot)", worker_id, order['order_id'])
                elif order.get("date", "").startswith("2026"):
                    retry_queue.append(order)
                    logging.info("[W%d] ⟳ Order %s (2026, will retry)", worker_id, order['order_id'])
                else:
                    results.append((order, None))
                    logging.info("[W%d] ⚠ Order %s (no output)", worker_id, order['order_id'])
            except Exception as e:
                if order.get("date", "").startswith("2026"):
                    retry_queue.append(order)
                    logging.info("[W%d] ⟳ Order %s error, will retry: %s", worker_id, order['order_id'], e)
                else:
                    logging.info("[W%d] ✗ Order %s: %s", worker_id, order['order_id'], e)
                    results.append((order, None))
            time.sleep(1)

        context.close()
        browser.close()

        # Retry failed 2026 orders with a fresh browser context
        if retry_queue:
            logging.info("[W%d] Retrying %d failed 2026 orders...", worker_id, len(retry_queue))
            browser = p.firefox.launch(headless=False)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                accept_downloads=True,
            )
            context.add_cookies(firefox_cookies)
            page = context.new_page()

            for order in retry_queue:
                try:
                    order, pdf_path = enrich_and_download(page, order, ecb_rates)
                    results.append((order, pdf_path))
                    is_pdf = pdf_path and str(pdf_path).endswith(".pdf")
                    status = "✓" if is_pdf else "📷" if pdf_path else "⚠"
                    logging.info("[W%d] %s Order %s (retry)", worker_id, status, order['order_id'])
                except Exception as e:
                    logging.info("[W%d] ✗ Order %s retry failed: %s", worker_id, order['order_id'], e)
                    results.append((order, None))
                time.sleep(2)

            context.close()
            browser.close()

    return results


def main():
    """Run the full AliExpress invoice grabber workflow."""
    load_dotenv(SCRIPT_DIR / ".env")

    # Set up logging to both console and file
    log_path = SCRIPT_DIR / "grabber.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(str(log_path), mode="w", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    ecb_rates = load_ecb_rates()

    # Extract cookies from the user's running Firefox
    print("Extracting cookies from Firefox...")
    profile_path = find_firefox_profile()
    firefox_cookies = extract_firefox_cookies(profile_path)

    if not firefox_cookies:
        print("ERROR: No AliExpress cookies found in Firefox.")
        print("Please log into AliExpress in Firefox first, then re-run.")
        sys.exit(1)

    print("\nStarting Playwright Firefox...")
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            accept_downloads=True,
        )

        # Inject Firefox cookies into the Playwright context
        context.add_cookies(firefox_cookies)

        page = context.new_page()
        page.goto(ALIEXPRESS_ORDER_LIST_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Check if login worked
        if "login" in page.url.lower():
            print("ERROR: Cookies expired or invalid. Please log into AliExpress")
            print("in Firefox again and re-run the script.")
            context.close()
            browser.close()
            sys.exit(1)

        print("Successfully logged in via Firefox cookies!")

        # Scrape orders from DOM — click "All" tab for complete list
        print("\nScraping orders...")

        # Click the "All" tab to see every order since account creation
        page.evaluate("""() => {
            const tabs = document.querySelectorAll('.comet-tabs-nav-item');
            for (const tab of tabs) {
                if (tab.textContent.trim() === 'All') {
                    tab.click();
                    return;
                }
            }
        }""")
        time.sleep(3)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        orders = scrape_order_list(page)

        if not orders:
            print("No orders found. The page structure may have changed.")
            print("Please check the browser window and ensure you're on the orders page.")
            context.close()
            browser.close()
            return

        print(f"\nFound {len(orders)} orders total.")

        # Pre-categorize all orders
        for order in orders:
            order["category"] = categorize_order(order["items"])

        context.close()
        browser.close()

    # Process orders in parallel using multiple headless browser instances
    num_workers = min(MAX_WORKERS, len(orders))
    print(f"\nProcessing {len(orders)} orders with {num_workers} parallel workers...")

    batch_size = math.ceil(len(orders) / num_workers)
    batches = [orders[i:i + batch_size] for i in range(0, len(orders), batch_size)]
    batch_args = [
        (batch, firefox_cookies, ecb_rates, worker_id)
        for worker_id, batch in enumerate(batches, 1)
    ]

    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(_process_order_batch, args) for args in batch_args]
        for future in concurrent.futures.as_completed(futures):
            all_results.extend(future.result())

    # Rebuild orders list and track download results
    orders = [result[0] for result in all_results]
    download_paths = {
        result[0]["order_id"]: result[1] for result in all_results
    }

    # Generate run report
    generate_run_report(orders, download_paths, ecb_rates)

    # Convert any remaining PNG screenshots to PDFs
    print("\nConverting remaining PNG screenshots to PDF...")
    png_converted = 0
    for year_dir in INVOICES_DIR.iterdir():
        if not year_dir.is_dir():
            continue
        for png_file in year_dir.glob("*.png"):
            pdf_file = png_file.with_suffix(".pdf")
            if not pdf_file.exists():
                if convert_png_to_pdf(png_file, pdf_file):
                    png_converted += 1
    print(f"  Converted {png_converted} PNG files to PDF.")

    # Generate yearly summaries
    print("\nGenerating yearly summaries...")
    years = sorted(set(o["date"][:4] for o in orders if len(o["date"]) >= 4))
    for year in years:
        year_orders = [o for o in orders if o["date"].startswith(year)]
        generate_yearly_summary(year, year_orders, ecb_rates, ANALYSIS_DIR)

    # Copy electronics invoices to dedicated folder
    print("\nOrganizing electronics invoices...")
    copy_electronics_invoices(orders, ELECTRONICS_DIR)

    # Generate overall order summary
    print("\nGenerating order summary...")
    generate_order_summary(orders, ecb_rates, SCRIPT_DIR / "orders_summary.md")

    # Generate Octopart search report for electronics items
    print("\nGenerating Octopart search report...")
    generate_octopart_report(orders, ANALYSIS_DIR / "octopart_search.md")

    # Build and display summary table
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
