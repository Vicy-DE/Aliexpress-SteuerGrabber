```instructions
---
applyTo: "**/*.py,**/*.ps1,**/*.sh,**/*.md,**/*.json,**/*.csv"
---

# Test Generation & Documentation — Instructions for Copilot

## When to execute

**After every implementation — before closing the task.**
Generate and run tests that cover the new or modified code. Document all executed tests in `Documentation/Tests/`.

---

## Step 1 — Generate tests

### Where to put test scripts
- Python unit tests → `tests/test_<module>.py`
- Integration / end-to-end tests → `tests/test_integration_<feature>.py`

### What to test — MANDATORY coverage

| Scope | What to verify |
|---|---|
| **Happy path** | Nominal input → expected output |
| **Error paths** | Missing cookies, invalid date format, missing ECB rates, network timeout |
| **Boundary conditions** | Zero price, empty item list, date on weekend/holiday, very long item titles |
| **Regression** | Previously passing tests still pass after the change |
| **Data accuracy** | EUR conversion rounded up correctly, category classification matches keywords |

### Test script conventions
- Use `pytest` as the test framework.
- Each test function is prefixed with `test_`.
- Tests must be runnable without a live AliExpress session (mock browser/network).
- Exit with code `0` on full pass, non-zero on any failure.
- Use `unittest.mock` to mock network calls, browser interactions, and file I/O.

### Run syntax check first
```powershell
py -3 -m py_compile grabber.py
```
Fix all errors before running any test.

---

## Step 2 — Execute tests

Run the test suite and capture output:

```powershell
py -3 -m pytest tests/ -v 2>&1 | Tee-Object -FilePath "Documentation/Tests/<YYYY-MM-DD>_<feature>_results.txt"
```

- **All tests MUST pass** before the task is considered done.
- If a test fails, fix the implementation and re-run.
- Never mark tests as "passed" without actual execution output.

---

## Step 3 — Document the tests

Create (or update) a test report in `Documentation/Tests/`.

### File naming

```
Documentation/Tests/<YYYY-MM-DD>_<feature>.md
```

### Report format

```markdown
# Test Report — <Feature / Change Title>

**Date:** YYYY-MM-DD
**Python version:** <py -3 --version>
**Script tested:** `grabber.py` (or specific module)

---

## Summary

| Result | Count |
|---|---|
| PASS | N |
| FAIL | 0 |

---

## Test Cases

### TC-01 — <Short test name>

**Script:** `tests/test_<module>.py::test_<name>`
**Input / stimulus:** <what was provided>
**Expected result:** <what should happen>
**Actual result:** PASS / FAIL — <one-line observation>

---

### TC-02 — <Short test name>

...

---

## Raw output

\```
<paste or summarise critical lines from pytest output>
\```

---

## Remarks

<Optional: edge cases discovered, deferred issues, manual verification notes.>
```

---

## Rules

- **MUST** generate tests for every code change.
- **MUST** run tests and confirm all pass before completing a task.
- **MUST** save a test report in `Documentation/Tests/` for every test session.
- **MUST NOT** mark tests as passed without actual execution.
- **SHOULD** prefer automated tests over manual verification where possible.
- **SHOULD** mock external dependencies (AliExpress, ECB API) in unit tests.
```
