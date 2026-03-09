# Test Report — Initial Implementation

**Date:** 2026-03-09
**Python version:** 3.14.3
**Script tested:** `grabber.py` — all pure logic functions
**Test framework:** pytest 9.0.2

---

## Summary

| Result | Count |
|---|---|
| PASS | 38 |
| FAIL | 0 |

---

## Test Cases

### EUR Conversion (8 tests)

### TC-01 — Exact date match

**Script:** `tests/test_grabber.py::TestUsdToEurRoundedUp::test_exact_date_match`
**Input:** $10.30 on 2025-01-14 (rate 1.0300)
**Expected:** EUR = ceil(10.30 / 1.0300 * 100) / 100, rate date = 2025-01-14
**Actual:** PASS

### TC-02 — Weekend falls back to Friday

**Script:** `tests/test_grabber.py::TestUsdToEurRoundedUp::test_weekend_falls_back_to_friday`
**Input:** $5.00 on 2025-01-11 (Saturday, no rate)
**Expected:** Use Friday 2025-01-10 rate (1.0200)
**Actual:** PASS

### TC-03 — Sunday falls back to Friday

**Script:** `tests/test_grabber.py::TestUsdToEurRoundedUp::test_sunday_falls_back_to_friday`
**Input:** $5.00 on 2025-01-12 (Sunday)
**Expected:** Fall back to 2025-01-10
**Actual:** PASS

### TC-04 — Rounds up not down

**Script:** `tests/test_grabber.py::TestUsdToEurRoundedUp::test_rounds_up_not_down`
**Input:** $10.00 / 1.025 = 9.75609...
**Expected:** €9.76 (ceiling, not floor/round)
**Actual:** PASS

### TC-05 — Zero price

**Script:** `tests/test_grabber.py::TestUsdToEurRoundedUp::test_zero_price`
**Input:** $0.00
**Expected:** €0.00
**Actual:** PASS

### TC-06 — Large amount

**Script:** `tests/test_grabber.py::TestUsdToEurRoundedUp::test_large_amount`
**Input:** $999.99
**Expected:** Correct ceiling conversion
**Actual:** PASS

### TC-07 — Fallback to most recent rate

**Script:** `tests/test_grabber.py::TestUsdToEurRoundedUp::test_fallback_to_most_recent_rate`
**Input:** Date 2025-06-01 (far from any known rate)
**Expected:** Use most recent rate (2025-01-15)
**Actual:** PASS

### TC-08 — Empty rates returns 1:1

**Script:** `tests/test_grabber.py::TestUsdToEurRoundedUp::test_empty_rates_returns_one_to_one`
**Input:** Empty rate dict
**Expected:** $10.00 → €10.00 with rate 1.0
**Actual:** PASS

---

### Date Parsing (11 tests)

### TC-09 — US format (Jan 15, 2025)

**Actual:** PASS — parsed to 2025-01-15

### TC-10 — US format full month (January 15, 2025)

**Actual:** PASS — parsed to 2025-01-15

### TC-11 — ISO format (2025-01-15)

**Actual:** PASS — parsed to 2025-01-15

### TC-12 — European dot format (15.01.2025)

**Actual:** PASS — parsed to 2025-01-15

### TC-13 — European slash format (15/01/2025)

**Actual:** PASS — parsed to 2025-01-15

### TC-14 — With "Order date:" prefix

**Actual:** PASS — prefix stripped, date parsed

### TC-15 — With "Paid on" prefix

**Actual:** PASS — prefix stripped, date parsed

### TC-16 — Day month year with spaces (15 Jan 2025)

**Actual:** PASS — parsed to 2025-01-15

### TC-17 — Empty string returns empty

**Actual:** PASS — returns ""

### TC-18 — Garbage text returns as-is

**Actual:** PASS — returns "not a date"

### TC-19 — ISO with dots (2025.01.15)

**Actual:** PASS — parsed to 2025-01-15

---

### Order Categorization (14 tests)

### TC-20 — Resistor → Electronics

**Actual:** PASS

### TC-21 — Arduino → Electronics

**Actual:** PASS

### TC-22 — ESP32 → Electronics

**Actual:** PASS

### TC-23 — Multimeter → Electronics

**Actual:** PASS

### TC-24 — Soldering iron → Electronics

**Actual:** PASS

### TC-25 — Clothing → Other

**Actual:** PASS

### TC-26 — Kitchen → Other

**Actual:** PASS

### TC-27 — Phone case → Other

**Actual:** PASS

### TC-28 — Mixed order (electronics wins)

**Actual:** PASS — one electronics item classifies the whole order

### TC-29 — Empty items → Other

**Actual:** PASS

### TC-30 — Case insensitive (CAPACITOR)

**Actual:** PASS

### TC-31 — USB cable → Electronics

**Actual:** PASS

### TC-32 — Servo → Electronics

**Actual:** PASS

### TC-33 — 3D print → Electronics

**Actual:** PASS

---

### Raw Order Parsing (5 tests)

### TC-34 — Normal order

**Actual:** PASS — order_id, date, price, items all parsed correctly

### TC-35 — Price with comma ($1,234.56)

**Actual:** PASS — parsed to 1234.56

### TC-36 — Missing price

**Actual:** PASS — defaults to 0.0

### TC-37 — Missing date

**Actual:** PASS — defaults to ""

### TC-38 — Euro price format (€9.99)

**Actual:** PASS — parsed to 9.99

---

## Raw output

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\Layer\Documents\Aliexpress-SteuerGrabber
collected 38 items

tests/test_grabber.py ......................................             [100%]

============================= 38 passed in 0.18s ==============================
```

---

## Remarks

- All 38 tests cover pure logic functions (no browser/network dependency).
- Browser-dependent functions (cookie extraction, scraping, PDF download) require manual verification with a live Firefox session.
- ECB rate fallback logic handles weekends, holidays, and missing data correctly.
- Rounding is verified to always ceil (never under-declare tax amounts).
