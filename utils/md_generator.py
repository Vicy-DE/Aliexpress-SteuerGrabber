"""Markdown invoice generation for individual orders.

Creates a companion .md file for each downloaded order containing
structured invoice data, EUR conversion details, and component
identification for electronics orders.
"""

from utils.categorizer import extract_part_numbers, lookup_part
from utils.exchange import usd_to_eur_rounded_up


def generate_invoice_md(receipt_data, order, md_path, ecb_rates):
    """Generate a Markdown invoice file for a single order.

    Args:
        receipt_data: Dict with structured receipt data (or None).
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

    lines += ["", "## Financial Summary", ""]

    if receipt_data:
        for label, key in [
            ("Subtotal", "subtotal"), ("Discount", "discount"),
            ("Shipping", "shipping"), ("VAT", "vat"), ("Total", "total"),
        ]:
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

    # Component identification for electronics orders
    if order.get("category") == "Electronics":
        item_titles = []
        if receipt_data and receipt_data.get("items"):
            item_titles = [
                i.get("title", "") for i in receipt_data["items"]
                if i.get("title")
            ]
        elif order.get("items"):
            item_titles = order["items"]
        if item_titles:
            lines += ["## Component Identification", ""]
            for title in item_titles:
                parts = extract_part_numbers(title)
                if parts:
                    info_parts = []
                    for pn in parts:
                        info = lookup_part(pn)
                        if info:
                            info_parts.append(
                                f"**{pn}** ({info['manufacturer']}"
                                f" — {info['description']})"
                            )
                        else:
                            info_parts.append(f"**{pn}**")
                    lines.append(f"- {'; '.join(info_parts)} — {title}")
                else:
                    lines.append(f"- {title}")
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
