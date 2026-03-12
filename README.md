# AliExpress-SteuerGrabber

Download all AliExpress invoice PDFs and generate a categorized summary table with EUR conversion for German tax declarations.

## Setup

```bash
pip install -r requirements.txt
playwright install firefox
```

## Usage

1. Open Firefox and log into [AliExpress](https://www.aliexpress.com/)
2. Run the script (keep Firefox open):

```bash
python grabber.py
```

The script will:
1. Extract session cookies from your running Firefox browser
2. Open a Playwright Firefox window using those cookies (no manual login needed)
3. Scrape all completed orders
4. Download invoice PDFs to `invoices/`
5. Look up USD→EUR exchange rates for each order date (ECB data)
6. Categorize each order (electronics vs. other)
7. Output a summary table to the console and `orders_summary.csv`

## Output

- `invoices/<order_id>.pdf` — individual invoice PDFs
- `orders_summary.csv` — categorized order table with EUR prices
