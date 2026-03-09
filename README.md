# AliExpress-SteuerGrabber

Download all AliExpress invoice PDFs and generate a categorized summary table with EUR conversion for German tax declarations.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Configuration

Copy `.env.example` to `.env` and fill in your AliExpress credentials:

```bash
cp .env.example .env
```

## Usage

```bash
python grabber.py
```

The script will:
1. Log into AliExpress using browser automation (manual login on first run)
2. Scrape all completed orders
3. Download invoice PDFs to `invoices/`
4. Look up USD→EUR exchange rates for each order date (ECB data)
5. Categorize each order (electronics vs. other)
6. Output a summary table to the console and `orders_summary.csv`

## Output

- `invoices/<order_id>.pdf` — individual invoice PDFs
- `orders_summary.csv` — categorized order table with EUR prices
