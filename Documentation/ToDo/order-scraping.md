# Todo: Order Scraping

**Created:** 2026-03-09
**Requirement:** [Req #2 — Order Scraping](../Requirements/requirements.md)
**Status:** Done

---

## Tasks

- [x] Inject Firefox cookies into Playwright Firefox context
- [x] Navigate to AliExpress order list page
- [x] Detect login failure (expired cookies) and abort with message
- [x] Implement API interception via network response listener
  - [x] Listen for `orderList` / `order/list` / `api/order` responses
  - [x] Parse common API response structures (`data.orderList`, `result.orders`, etc.)
  - [x] Extract order ID, date, price, item titles from API responses
- [x] Implement DOM scraping fallback
  - [x] Try multiple CSS selector patterns for order cards
  - [x] JavaScript-based extraction as final fallback
  - [x] Extract order ID, date, price, item titles from DOM
- [x] Handle pagination (click next button until no more pages)
- [x] Parse multiple AliExpress date formats to YYYY-MM-DD
  - [x] "Jan 15, 2025", "2025-01-15", "15.01.2025", "15/01/2025", etc.
  - [x] Handle date prefixes ("Order date:", "Paid on", etc.)
- [x] Enrich orders with missing data from detail pages
- [x] Switch to "Completed" / "Abgeschlossen" tab if available
- [x] Script runs without errors
- [x] CHANGE_LOG.md updated

---

## Notes

- AliExpress frequently changes their DOM structure; selectors may need updating.
- API interception is tried first as it provides cleaner data than DOM scraping.
