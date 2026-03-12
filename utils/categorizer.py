"""Order categorisation, part-number extraction and component lookup.

Classifies orders as Electronics / Automotive / Other using keyword
matching, extracts electronic part numbers via regex patterns, and
looks up components in the curated local database.
"""

import re

from utils.config import (
    AUTOMOTIVE_KEYWORDS,
    ELECTRONICS_KEYWORDS,
    PART_DATABASE,
    PART_NUMBER_PATTERNS,
)


def categorize_order(item_titles):
    """Categorize an order as Electronics, Automotive, or Other.

    Uses word-boundary regex matching so that e.g. "motor" does not
    match "Motorcycle". Items that match automotive keywords are
    classified as "Automotive" regardless of electronics keywords.

    Args:
        item_titles: List of item title strings from the order.

    Returns:
        "Electronics", "Automotive", or "Other".
    """
    combined = " ".join(item_titles).lower()

    for keyword in AUTOMOTIVE_KEYWORDS:
        pattern = r"\b" + re.escape(keyword.strip()) + r"\b"
        if re.search(pattern, combined):
            return "Automotive"

    for keyword in ELECTRONICS_KEYWORDS:
        pattern = r"\b" + re.escape(keyword.strip()) + r"\b"
        if re.search(pattern, combined):
            return "Electronics"

    return "Other"


def extract_part_numbers(title):
    """Extract likely electronic component part numbers from a product title.

    Looks for common part number patterns (chip families, passives,
    connectors, etc.) and returns a list of matches.

    Args:
        title: Product title string.

    Returns:
        List of extracted part number strings.
    """
    parts = []
    for pat in PART_NUMBER_PATTERNS:
        for match in re.finditer(pat, title, re.IGNORECASE):
            part = match.group(1).upper()
            if part not in parts:
                parts.append(part)
    return parts


def lookup_part(part_number):
    """Look up a part number in the local component database.

    Tries exact match first, then prefix match for chip families.

    Args:
        part_number: Uppercase part number string.

    Returns:
        Dict with manufacturer and description, or None if not found.
    """
    part = part_number.upper()
    if part in PART_DATABASE:
        return PART_DATABASE[part]
    for db_part, info in PART_DATABASE.items():
        if part.startswith(db_part) or db_part.startswith(part):
            return info
    return None
