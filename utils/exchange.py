"""ECB exchange-rate fetching and USD-to-EUR conversion.

Fetches historical USD/EUR daily reference rates from the ECB XML feed,
caches them locally for 24 hours, and provides a rounding-up conversion
function suitable for German tax declarations.
"""

import json
import math
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests

from utils.config import ECB_NS, ECB_RATES_URL, SCRIPT_DIR


def load_ecb_rates():
    """Fetch ECB historical USD/EUR exchange rates.

    Returns:
        Dict mapping date string (YYYY-MM-DD) to USD-per-EUR rate (float).
    """
    cache_file = SCRIPT_DIR / "ecb_rates_cache.json"

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

    for delta in range(8):
        check_date = (date - timedelta(days=delta)).strftime("%Y-%m-%d")
        if check_date in ecb_rates:
            usd_per_eur = ecb_rates[check_date]
            eur = usd_amount / usd_per_eur
            eur_rounded = math.ceil(eur * 100) / 100
            return eur_rounded, usd_per_eur, check_date

    sorted_dates = sorted(ecb_rates.keys(), reverse=True)
    if sorted_dates:
        fallback_date = sorted_dates[0]
        usd_per_eur = ecb_rates[fallback_date]
        eur = usd_amount / usd_per_eur
        eur_rounded = math.ceil(eur * 100) / 100
        return eur_rounded, usd_per_eur, fallback_date

    return usd_amount, 1.0, order_date_str
