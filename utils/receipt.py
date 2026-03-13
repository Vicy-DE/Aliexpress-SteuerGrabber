"""AliExpress receipt data extraction from the tax-ui page.

Navigates to the AliExpress tax-ui URL for a given order and scrapes
structured receipt data (items, prices, addresses, payment info) from
the rendered DOM.  Also supports downloading the official receipt PNG
via the page's Download button.
"""

import base64
import time

from utils.config import ALIEXPRESS_TAX_UI_URL


def _navigate_to_tax_ui(page, order_id):
    """Navigate to the tax-ui page and wait for receipt content.

    Args:
        page: Playwright page object.
        order_id: AliExpress order ID string.

    Returns:
        True if receipt content rendered, False otherwise.
    """
    tax_url = ALIEXPRESS_TAX_UI_URL.format(order_id=order_id)
    try:
        page.goto(tax_url)
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception as exc:
        print(f"    tax-ui page failed to load: {exc}")
        return False
    time.sleep(3)

    # Wait for receipt content to render (React hydration)
    for _attempt in range(15):
        has_content = page.evaluate("""
            () => document.querySelectorAll(
                '[class*="summary--row"]'
            ).length > 0
        """)
        if has_content:
            return True
        time.sleep(1)

    print("    tax-ui page has no receipt content.")
    return False


def download_receipt_image(page, order_id, save_path):
    """Download the official receipt PNG via the tax-ui Download button.

    Navigates to the tax-ui page, intercepts the download anchor's
    data URL via JavaScript, and saves the decoded PNG to save_path.

    Args:
        page: Playwright page object.
        order_id: AliExpress order ID string.
        save_path: Path where the PNG should be saved.

    Returns:
        True if download succeeded, False otherwise.
    """
    if not _navigate_to_tax_ui(page, order_id):
        return False

    # Find the Download button
    download_btn = page.locator(
        '[class*="bar--btn"]', has_text="Download"
    )
    if download_btn.count() == 0:
        print("    No Download button found on tax-ui page.")
        return False

    # Intercept anchor creation to capture the data URL, then click
    data_url = page.evaluate("""() => {
        return new Promise((resolve) => {
            const origCreate = document.createElement.bind(document);
            document.createElement = function(tag, opts) {
                const el = origCreate(tag, opts);
                if (tag.toLowerCase() === 'a') {
                    const origClick = el.click.bind(el);
                    el.click = function() {
                        if (el.href && el.href.startsWith('data:')) {
                            resolve(el.href);
                        } else {
                            origClick();
                        }
                    };
                }
                return el;
            };
            const btn = document.querySelector(
                '[class*="bar--btn"][class*="black"]'
            );
            if (btn) btn.click();
            setTimeout(() => resolve(null), 15000);
        });
    }""")

    if not data_url or not data_url.startswith("data:image/png;base64,"):
        print("    Could not capture receipt image data URL.")
        return False

    # Decode base64 and save as PNG
    b64_data = data_url.split(",", 1)[1]
    img_bytes = base64.b64decode(b64_data)
    with open(str(save_path), "wb") as f:
        f.write(img_bytes)
    return True


def extract_receipt_data(page, order_id):
    """Extract structured receipt data from the AliExpress tax-ui page.

    Assumes the page is already on the tax-ui page (navigated by the
    caller or by download_receipt_image).  If not, navigates there.

    Args:
        page: Playwright page object.
        order_id: AliExpress order ID string.

    Returns:
        Dict with receipt data, or None if extraction failed.
    """
    # Navigate only if not already on the tax-ui page for this order
    current = page.url
    if str(order_id) not in current or "tax-ui" not in current:
        if not _navigate_to_tax_ui(page, order_id):
            return None

    data = page.evaluate(_RECEIPT_EXTRACTION_JS)
    return data


# JavaScript executed in the browser to extract receipt fields.
_RECEIPT_EXTRACTION_JS = """() => {
    const result = {
        order_id: '', order_time: '', items: [],
        subtotal: '', discount: '', shipping: '', total: '', vat: '',
        address_lines: [], payment_method: ''
    };

    const rows = document.querySelectorAll('[class*="summary--row"]');
    rows.forEach(row => {
        const label = row.querySelector('[class*="summary--left"]');
        const value = row.querySelector('[class*="summary--right"]');
        if (!label || !value) return;
        const l = label.textContent.trim().toLowerCase();
        const v = value.textContent.trim();
        if (l.includes('order id') || l.includes('order number'))
            result.order_id = v;
        else if (l.includes('order time') || l.includes('date'))
            result.order_time = v;
        else if (l.includes('subtotal')) result.subtotal = v;
        else if (l.includes('discount')) result.discount = v;
        else if (l.includes('shipping')) result.shipping = v;
        else if (l.includes('vat') || l.includes('tax')) result.vat = v;
        else if (l.includes('total') && !l.includes('sub'))
            result.total = v;
    });

    const products = document.querySelectorAll(
        '[class*="products--product--"]'
    );
    products.forEach(product => {
        const titleEl = product.querySelector('[class*="product-title"]');
        const priceEl = product.querySelector('[class*="product-price"]');
        const skuEl   = product.querySelector('[class*="product-sku"]');
        result.items.push({
            title:    titleEl ? titleEl.textContent.trim() : '',
            price:    priceEl ? priceEl.textContent.trim() : '',
            sku:      skuEl   ? skuEl.textContent.trim()   : '',
            quantity: '1',
        });
    });

    if (result.items.length === 0) {
        const prodContainer = document.querySelector(
            '[class*="products--container"]'
        );
        if (prodContainer) {
            const text = prodContainer.innerText.trim();
            if (text) result.items.push(
                {title: text, price: '', sku: '', quantity: '1'}
            );
        }
    }

    const addrContainer = document.querySelector(
        '[class*="address--container"]'
    );
    if (addrContainer) {
        result.address_lines = addrContainer.innerText
            .trim().split('\\n').filter(l => l.trim());
    }

    const payContainer = document.querySelector(
        '[class*="payment--container"]'
    );
    if (payContainer) {
        result.payment_method = payContainer.innerText.trim();
    }

    return result;
}"""
