"""AliExpress receipt data extraction from the tax-ui page.

Navigates to the AliExpress tax-ui URL for a given order and scrapes
structured receipt data (items, prices, addresses, payment info) from
the rendered DOM.
"""

import time

from utils.config import ALIEXPRESS_TAX_UI_URL


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
    for _attempt in range(15):
        has_content = page.evaluate("""
            () => document.querySelectorAll(
                '[class*="summary--row"]'
            ).length > 0
        """)
        if has_content:
            break
        time.sleep(1)

    if not has_content:
        print("    tax-ui page has no receipt content.")
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
