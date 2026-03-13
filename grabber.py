"""AliExpress invoice grabber - main entry point.

Thin orchestration layer that delegates to utils/ modules for
cookie extraction, order scraping, receipt downloading, PDF/MD
generation, and summary reporting.
"""

import concurrent.futures
import logging
import math
import sys
import time

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from utils.categorizer import categorize_order
from utils.config import (
    ALIEXPRESS_ORDER_LIST_URL,
    ANALYSIS_DIR,
    ELECTRONICS_DIR,
    INVOICES_DIR,
    MAX_WORKERS,
    SCRIPT_DIR,
)
from utils.downloader import process_order_batch
from utils.exchange import load_ecb_rates
from utils.firefox import extract_firefox_cookies, find_firefox_profile
from utils.pdf_generator import convert_png_to_pdf
from utils.reports import (
    build_summary_table,
    copy_electronics_invoices,
    export_csv,
    generate_octopart_report,
    generate_order_summary,
    generate_run_report,
    generate_yearly_summary,
    print_summary,
)
from utils.scraper import scrape_order_list


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

        # Scrape orders from DOM - click "All" tab for complete list
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

    # Process orders in parallel using multiple browser instances
    num_workers = min(MAX_WORKERS, len(orders))
    print(f"\nProcessing {len(orders)} orders with {num_workers} parallel workers...")

    batch_size = math.ceil(len(orders) / num_workers)
    batches = [
        orders[i:i + batch_size]
        for i in range(0, len(orders), batch_size)
    ]
    batch_args = [
        (batch, firefox_cookies, ecb_rates, worker_id)
        for worker_id, batch in enumerate(batches, 1)
    ]

    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(process_order_batch, args)
            for args in batch_args
        ]
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
    order_by_file = {}
    for o in orders:
        date_str = o.get("date", "unknown")
        key = f"{date_str}-{o['order_id']}"
        order_by_file[key] = o

    png_converted = 0
    for year_dir in INVOICES_DIR.iterdir():
        if not year_dir.is_dir():
            continue
        for order_dir in year_dir.iterdir():
            if not order_dir.is_dir():
                continue
            for png_file in order_dir.glob("*.png"):
                pdf_file = png_file.with_suffix(".pdf")
                if not pdf_file.exists():
                    file_key = png_file.stem
                    matched_order = order_by_file.get(file_key)
                    if convert_png_to_pdf(png_file, pdf_file, order=matched_order):
                        png_converted += 1
    print(f"  Converted {png_converted} PNG files to PDF.")

    # Generate yearly summaries
    print("\nGenerating yearly summaries...")
    years = sorted(
        set(o["date"][:4] for o in orders if len(o["date"]) >= 4)
    )
    for year in years:
        year_orders = [o for o in orders if o["date"].startswith(year)]
        generate_yearly_summary(year, year_orders, ecb_rates, ANALYSIS_DIR)

    # Copy electronics invoices to dedicated folder
    print("\nOrganizing electronics invoices...")
    copy_electronics_invoices(orders, ELECTRONICS_DIR)

    # Generate overall order summary
    print("\nGenerating order summary...")
    generate_order_summary(
        orders, ecb_rates, SCRIPT_DIR / "orders_summary.md"
    )

    # Generate Octopart search report for electronics items
    print("\nGenerating electronics part report...")
    generate_octopart_report(orders, ANALYSIS_DIR / "octopart_search.md")

    # Build and display summary table, export CSV
    rows = build_summary_table(orders, ecb_rates)
    print_summary(rows)
    export_csv(rows)


if __name__ == "__main__":
    main()