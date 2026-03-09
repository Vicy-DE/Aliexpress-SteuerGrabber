# Todo: EUR Conversion

**Created:** 2026-03-09
**Requirement:** [Req #4 — EUR Conversion](../Requirements/requirements.md)
**Status:** Done

---

## Tasks

- [x] Fetch ECB historical USD/EUR rates from XML feed
  - [x] Parse XML with namespaces (`gesmes`, `ecb`)
  - [x] Extract date → USD-per-EUR rate mapping
- [x] Cache rates to `ecb_rates_cache.json`
  - [x] Use cache if less than 24 hours old
- [x] Find rate for order date
  - [x] If exact date has no rate (weekend/holiday), search up to 7 days back
  - [x] Fallback to most recent rate if nothing found in 7-day window
- [x] Convert USD to EUR: `usd_amount / usd_per_eur`
- [x] Round up to next full cent: `math.ceil(eur * 100) / 100`
- [x] Return rate used and rate date for traceability
- [x] Script runs without errors
- [x] CHANGE_LOG.md updated

---

## Notes

- ECB daily feed covers ~90 days of history. For older orders, the fallback uses the most recent available rate.
- The "rounded up" requirement ensures tax amounts are never under-declared.
