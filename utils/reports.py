"""Summary reports, CSV export, and run-report generation.

Generates yearly summaries, overall order summary, electronics part
identification report, run reports, and CSV exports.
"""

import csv
import math
import shutil
from datetime import datetime

from tabulate import tabulate

from utils.categorizer import categorize_order, extract_part_numbers, lookup_part
from utils.config import ANALYSIS_DIR, INVOICES_DIR, OCTOPART_SEARCH_URL, OUTPUT_CSV, SCRIPT_DIR
from utils.exchange import usd_to_eur_rounded_up


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
            "Items": (
                "; ".join(order["items"])[:80]
                if order["items"] else "(no title)"
            ),
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
    electronics_orders = [
        o for o in year_orders if o.get("category") == "Electronics"
    ]
    automotive_orders = [
        o for o in year_orders if o.get("category") == "Automotive"
    ]
    other_orders = [
        o for o in year_orders
        if o.get("category") not in ("Electronics", "Automotive")
    ]

    electronics_usd = sum(o["total_usd"] for o in electronics_orders)
    automotive_usd = sum(o["total_usd"] for o in automotive_orders)
    other_usd = sum(o["total_usd"] for o in other_orders)

    lines = [
        f"# Yearly Summary \u2014 {year}",
        "",
        f"**Total Orders:** {len(year_orders)}",
        f"**Electronics Orders:** {len(electronics_orders)}",
        f"**Automotive Orders:** {len(automotive_orders)}",
        f"**Other Orders:** {len(other_orders)}",
        "",
        "## All Orders",
        "",
        "| Date | Order ID | Items | Category | USD | EUR |",
        "|------|----------|-------|----------|-----|-----|",
    ]

    total_eur = 0.0
    electronics_eur = 0.0
    automotive_eur = 0.0
    other_eur = 0.0

    for o in sorted(year_orders, key=lambda x: x["date"]):
        eur, _, _ = usd_to_eur_rounded_up(o["total_usd"], o["date"], ecb_rates)
        total_eur += eur
        if o.get("category") == "Electronics":
            electronics_eur += eur
        elif o.get("category") == "Automotive":
            automotive_eur += eur
        else:
            other_eur += eur
        items_str = (
            "; ".join(o["items"])[:60].replace("|", "/")
            if o["items"] else "(no title)"
        )
        cat = o.get("category", "Other")
        lines.append(
            f"| {o['date']} | {o['order_id']} | {items_str} | {cat} "
            f"| ${o['total_usd']:.2f} | €{eur:.2f} |"
        )

    lines += [
        "",
        "## Totals",
        "",
        "| Category | USD | EUR |",
        "|----------|-----|-----|",
        f"| Electronics | ${electronics_usd:.2f} | €{electronics_eur:.2f} |",
        f"| Automotive | ${automotive_usd:.2f} | €{automotive_eur:.2f} |",
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
    electronics_orders = [
        o for o in orders if o.get("category") == "Electronics"
    ]
    automotive_orders = [
        o for o in orders if o.get("category") == "Automotive"
    ]
    other_orders = [
        o for o in orders
        if o.get("category") not in ("Electronics", "Automotive")
    ]

    lines = [
        "# AliExpress Order Summary",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Total Orders:** {len(orders)}",
        f"**Electronics:** {len(electronics_orders)}",
        f"**Automotive:** {len(automotive_orders)}",
        f"**Other:** {len(other_orders)}",
        "",
        "## All Orders",
        "",
        "| # | Date | Order ID | Items | Category | USD | EUR |",
        "|---|------|----------|-------|----------|-----|-----|",
    ]

    grand_eur = 0.0
    for i, o in enumerate(sorted(orders, key=lambda x: x["date"]), 1):
        eur, _, _ = usd_to_eur_rounded_up(
            o["total_usd"], o["date"], ecb_rates
        )
        grand_eur += eur
        items_str = (
            "; ".join(o["items"])[:55].replace("|", "/")
            if o["items"] else "(no title)"
        )
        cat = o.get("category", "Other")
        lines.append(
            f"| {i} | {o['date']} | {o['order_id']} | {items_str} "
            f"| {cat} | ${o['total_usd']:.2f} | €{eur:.2f} |"
        )

    lines += ["", "## Summary by Year", ""]

    years = sorted(set(o["date"][:4] for o in orders if len(o["date"]) >= 4))
    for year in years:
        yo = [o for o in orders if o["date"].startswith(year)]
        y_usd = sum(o["total_usd"] for o in yo)
        y_eur = sum(
            usd_to_eur_rounded_up(o["total_usd"], o["date"], ecb_rates)[0]
            for o in yo
        )
        lines.append(
            f"- **{year}:** {len(yo)} orders — ${y_usd:.2f} / €{y_eur:.2f}"
        )

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

    electronics_orders = [
        o for o in orders if o.get("category") == "Electronics"
    ]
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


def generate_octopart_report(orders, output_path):
    """Generate a report with extracted part numbers for electronics items.

    Lists electronics order items with extracted component part numbers
    and local database lookup results (manufacturer + description).

    Args:
        orders: List of all order dicts.
        output_path: Path to save the report file.
    """
    electronics_orders = [
        o for o in orders if o.get("category") == "Electronics"
    ]
    if not electronics_orders:
        return

    lines = [
        "# Electronics Components — Part Identification",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Electronics Orders:** {len(electronics_orders)}",
        "",
        "| Date | Order ID | Item | Part Number(s) "
        "| Manufacturer | Description |",
        "|------|----------|------|----------------"
        "|--------------|-------------|",
    ]

    for order in sorted(electronics_orders, key=lambda x: x["date"]):
        if order["items"]:
            for item in order["items"]:
                parts = extract_part_numbers(item)
                parts_str = ", ".join(parts) if parts else "—"
                mfr = "—"
                desc = "—"
                if parts:
                    info = lookup_part(parts[0])
                    if info:
                        mfr = info["manufacturer"]
                        desc = info["description"]
                title = item[:60].replace("|", "/")
                lines.append(
                    f"| {order['date']} | {order['order_id']} | "
                    f"{title} | {parts_str} | {mfr} | {desc} |"
                )
        else:
            lines.append(
                f"| {order['date']} | {order['order_id']} | "
                f"*(no title)* | — | — | — |"
            )

    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Electronics part report saved: {output_path}")


def generate_run_report(orders, download_paths, ecb_rates):
    """Generate a comprehensive Markdown run report of all orders.

    Groups orders by year and shows download status.

    Args:
        orders: List of order dicts.
        download_paths: Dict mapping order_id to Path (or None).
        ecb_rates: ECB exchange rate dict.
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
        for i, order in enumerate(
            sorted(year_orders, key=lambda o: o["date"]), 1
        ):
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
            lines.append(
                f"\n**Year total:** ${year_total_usd:.2f}"
                f" ≈ €{year_total_eur:.2f}"
            )
        else:
            lines.append(f"\n**Year total:** ${year_total_usd:.2f}")
        lines.append("")

    # Failed downloads section
    failed = [o for o in orders if not download_paths.get(o["order_id"])]
    if failed:
        lines.append("## Failed Downloads")
        lines.append("")
        for order in failed:
            lines.append(
                f"- **{order['order_id']}** ({order['date']}): "
                f"{'; '.join(order['items'][:2])}"
            )
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRun report saved: {report_path}")


def print_summary(rows):
    """Print the summary table and category totals to console.

    Args:
        rows: List of row dicts from build_summary_table().
    """
    print("\n" + "=" * 100)
    print("ORDER SUMMARY")
    print("=" * 100)
    print(tabulate(rows, headers="keys", tablefmt="grid"))

    electronics_total_eur = sum(
        float(r["Price (EUR)"].replace("€", ""))
        for r in rows if r["Category"] == "Electronics"
    )
    automotive_total_eur = sum(
        float(r["Price (EUR)"].replace("€", ""))
        for r in rows if r["Category"] == "Automotive"
    )
    other_total_eur = sum(
        float(r["Price (EUR)"].replace("€", ""))
        for r in rows if r["Category"] == "Other"
    )
    total_eur = electronics_total_eur + automotive_total_eur + other_total_eur

    print(f"\nElectronics total: €{electronics_total_eur:.2f}")
    print(f"Automotive total:  €{automotive_total_eur:.2f}")
    print(f"Other total:       €{other_total_eur:.2f}")
    print(f"Grand total:       €{total_eur:.2f}")
