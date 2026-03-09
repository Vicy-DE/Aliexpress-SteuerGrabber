# Todo: Firefox Cookie Extraction

**Created:** 2026-03-09
**Requirement:** [Req #1 — Firefox Cookie Extraction](../Requirements/requirements.md)
**Status:** Done

---

## Tasks

- [x] Find Firefox profile directory via `profiles.ini`
  - [x] Parse `configparser` sections for default profile
  - [x] Handle both relative and absolute profile paths
  - [x] Handle `InstallXXX` sections with `Default=` key
- [x] Copy `cookies.sqlite` to temp directory to avoid lock conflicts
  - [x] Also copy WAL and SHM journal files if they exist
- [x] Query `moz_cookies` table for `.aliexpress.com` domain
- [x] Convert Firefox cookie fields to Playwright-compatible format
  - [x] Map `sameSite` integer values (0/1/2) to string ("None"/"Lax"/"Strict")
  - [x] Handle optional `expiry` field
- [x] Clean up temp directory after extraction
- [x] Abort with clear error if no cookies found
- [x] Script runs without errors
- [x] CHANGE_LOG.md updated

---

## Notes

- Firefox holds a WAL lock on `cookies.sqlite` while running — copying to temp is mandatory.
- The profile detection searches both `[ProfileN]` and `[InstallXXX]` sections in `profiles.ini`.
