"""Order-list scraping, API interception and date/price parsing.

Handles both DOM-based scraping of the AliExpress order list page and
MTOP API response interception.  Also provides date-format normalisation
and raw-order parsing helpers.
"""

import json
import re
import time
from datetime import datetime

from utils.config import ALIEXPRESS_ORDER_LIST_URL


# -------------------------------------------------------------------
# Date / price parsing helpers
# -------------------------------------------------------------------

def parse_aliexpress_date(date_raw):
    """Parse various AliExpress date formats to YYYY-MM-DD.

    Args:
        date_raw: Raw date string from AliExpress.

    Returns:
        Date string in YYYY-MM-DD format, or the raw string if parsing fails.
    """
    date_raw = date_raw.strip()
    for prefix in ["Order date:", "Paid on", "Payment date:", "Date:"]:
        date_raw = date_raw.replace(prefix, "").strip()

    formats = [
        "%b %d, %Y",
        "%B %d, %Y",
        "%Y-%m-%d",
        "%d %b %Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y.%m.%d",
        "%d.%m.%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", date_raw)
    if match:
        return (
            f"{match.group(1)}-{match.group(2).zfill(2)}"
            f"-{match.group(3).zfill(2)}"
        )

    return date_raw


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

    price_match = re.search(r"[\d]+[.,]?\d*", total_text.replace(",", ""))
    total_usd = (
        float(price_match.group().replace(",", ".")) if price_match else 0.0
    )

    date_str = parse_aliexpress_date(date_raw)

    return {
        "order_id": order_id,
        "date": date_str,
        "items": items,
        "total_usd": total_usd,
    }


# -------------------------------------------------------------------
# DOM scraping
# -------------------------------------------------------------------

def scrape_order_list(page):
    """Scrape all orders from the AliExpress order list pages via DOM.

    Uses JavaScript evaluation with the actual AliExpress CSS class
    structure. Scrolls and clicks "View orders" to paginate.

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
                const idEl = card.querySelector(
                    '.order-item-header-right-info, '
                    + '[class*="order-item-header-right"]'
                );
                let orderId = '';
                if (idEl) {
                    const idMatch = idEl.textContent.match(/\\d{10,}/);
                    if (idMatch) orderId = idMatch[0];
                }

                const headerEl = card.querySelector('.order-item-header');
                let dateStr = '';
                if (headerEl) {
                    const dateMatch = headerEl.textContent.match(
                        /Order date:\\s*([A-Za-z]+ \\d{1,2},\\s*\\d{4})/
                    );
                    if (dateMatch) dateStr = dateMatch[1];
                }

                const items = [];
                card.querySelectorAll(
                    '.order-item-content-info-name'
                ).forEach(el => {
                    const txt = el.textContent.trim();
                    if (txt) items.push(txt);
                });

                const priceEl = card.querySelector(
                    '.order-item-content-opt-price-total'
                );
                let totalText = '';
                if (priceEl) totalText = priceEl.textContent.trim();

                if (orderId) {
                    orders.push({
                        order_id: orderId,
                        date: dateStr,
                        total_text: totalText,
                        items: items,
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

        print(
            f"  Scroll {attempt + 1}: {len(orders)} orders total "
            f"(+{new_count} new)"
        )

        if new_count == 0:
            stale_rounds += 1
            if stale_rounds >= max_stale_rounds:
                print(
                    f"  No new orders for {max_stale_rounds} rounds, stopping."
                )
                break
        else:
            stale_rounds = 0

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

        has_more = page.evaluate("""() => {
            let btn = document.querySelector('.order-more button');
            if (btn && btn.offsetParent !== null) {
                btn.click();
                return true;
            }
            const candidates = document.querySelectorAll(
                'button, [class*="load-more"], '
                + '[class*="view-more"], [class*="order-more"]'
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
            break

    print(f"  Scraping complete: {len(orders)} orders found.")
    return orders


# -------------------------------------------------------------------
# API interception
# -------------------------------------------------------------------

def scrape_orders_via_api(page):
    """Scrape orders by intercepting AliExpress MTOP API responses.

    Args:
        page: Playwright page object.

    Returns:
        List of order dicts, or empty list if API interception fails.
    """
    orders = []
    api_responses = []

    def handle_response(response):
        """Capture MTOP order API responses."""
        url = response.url
        if "mtop.aliexpress.trade.buyer.order" in url.lower():
            try:
                body = response.text()
                match = re.search(
                    r"mtopjsonp\d+\((.+)\)\s*;?\s*$", body, re.DOTALL
                )
                if match:
                    data = json.loads(match.group(1))
                    api_responses.append(data)
                else:
                    data = json.loads(body)
                    api_responses.append(data)
            except Exception:
                pass

    page.on("response", handle_response)
    page.goto(ALIEXPRESS_ORDER_LIST_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    for resp_body in api_responses:
        try:
            order_list = _extract_order_list(resp_body)
            if not order_list:
                continue

            for api_order in order_list:
                if not isinstance(api_order, dict):
                    continue
                order = _parse_api_order(api_order)
                if order["order_id"]:
                    orders.append(order)
        except Exception:
            continue

    page.remove_listener("response", handle_response)
    return orders


def _extract_order_list(resp_body):
    """Extract the order list from a MTOP API response body.

    Args:
        resp_body: Parsed JSON response dict.

    Returns:
        List of order dicts, or None.
    """
    if not isinstance(resp_body, dict):
        return None

    data = resp_body.get("data", {})
    if not isinstance(data, dict):
        return None

    order_list = data.get("orderList", data.get("orders", data.get("list")))
    if not order_list:
        result = data.get("result", data.get("body", {}))
        if isinstance(result, dict):
            order_list = result.get("orderList", result.get("orders"))
        elif isinstance(result, list):
            order_list = result

    if order_list and isinstance(order_list, list):
        return order_list
    return None


def _parse_api_order(api_order):
    """Parse a single order from the MTOP API response.

    Args:
        api_order: Single order dict from the API.

    Returns:
        Standardised order dict.
    """
    order = {
        "order_id": str(api_order.get("orderId", api_order.get("id", ""))),
        "date": "",
        "items": [],
        "total_usd": 0.0,
    }

    for date_key in ["orderDate", "createDate", "gmtCreate", "payTime"]:
        if date_key in api_order:
            order["date"] = parse_aliexpress_date(str(api_order[date_key]))
            break

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

    for items_key in ["productList", "items", "orderItems", "childOrderList"]:
        if items_key in api_order:
            for item in api_order[items_key]:
                if isinstance(item, dict):
                    for title_key in [
                        "productName", "title", "name", "itemTitle"
                    ]:
                        if title_key in item:
                            order["items"].append(item[title_key])
                            break

    return order
