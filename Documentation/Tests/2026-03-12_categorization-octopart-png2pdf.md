# Test Report — Automotive Exclusion, Part Number Extraction, PNG→PDF Conversion

**Date:** 2026-03-12
**Python version:** 3.14.3
**Script tested:** `grabber.py`

---

## Summary

| Result | Count |
|---|---|
| PASS | 78 |
| FAIL | 0 |

---

## New Test Cases

### TC-01 — Motorcycle CNC part is Other

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_motorcycle_cnc_part_is_other`
**Input:** Item title containing "motorcycle" + "CNC" (would previously match electronics via "cnc")
**Expected result:** "Other" (automotive exclusion overrides electronics match)
**Actual result:** PASS

### TC-02 — Car diagnostic HEX V2 is Other

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_car_diagnostic_hex_v2_is_other`
**Input:** "Real ARM STM32F429 Chip For VAG HEX V2"
**Expected result:** "Other" (automotive exclusion via "HEX V2" overrides "STM32" electronics match)
**Actual result:** PASS

### TC-03 — OBD scanner is Other

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_obd_scanner_is_other`
**Input:** "Super Mini ELM327 OBD2 Diagnostic Scanner"
**Expected result:** "Other"
**Actual result:** PASS

### TC-04 — Flex fuel sensor is Other

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_flex_fuel_sensor_is_other`
**Input:** "New Flex Fuel Composition Sensor E85 for GM Cadillac"
**Expected result:** "Other" (automotive exclusion via "flex fuel" overrides "sensor" match)
**Actual result:** PASS

### TC-05 — O2 sensor is Other

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_o2_sensor_is_other`
**Input:** "Universal Oxygen O2 Sensor Lambda Sensor"
**Expected result:** "Other"
**Actual result:** PASS

### TC-06 — Starter relay motorcycle is Other

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_starter_relay_motorcycle_is_other`
**Input:** "Motorcycle Starter Solenoid Relay"
**Expected result:** "Other" (automotive exclusion via "motorcycle" overrides "relay" match)
**Actual result:** PASS

### TC-07 — Motorcycle kill switch is Other

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_motorcycle_kill_switch_is_other`
**Input:** "Motorcycle Handlebar Kill Switch"
**Expected result:** "Other"
**Actual result:** PASS

### TC-08 — Openport ECU flash is Other

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_openport_ecu_flash_is_other`
**Input:** "Openport 2.0 ECU FLASH Chip Tuning"
**Expected result:** "Other" (automotive exclusion via "openport" overrides "programmer" match)
**Actual result:** PASS

### TC-09 — Pure ESP32 still Electronics

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_pure_esp32_still_electronics`
**Input:** "ESP32 Dev Board WiFi Bluetooth"
**Expected result:** "Electronics" (no automotive keywords present)
**Actual result:** PASS

### TC-10 — Pure Arduino still Electronics

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_pure_arduino_still_electronics`
**Input:** "Arduino Nano V3.0 ATmega328"
**Expected result:** "Electronics"
**Actual result:** PASS

### TC-11 — Pure resistor still Electronics

**Script:** `tests/test_grabber.py::TestAutomotiveExclusion::test_pure_resistor_still_electronics`
**Input:** "100pcs 10K Ohm Resistor 1/4W"
**Expected result:** "Electronics"
**Actual result:** PASS

### TC-12 — Extract ESP32 part number

**Script:** `tests/test_grabber.py::TestExtractPartNumbers::test_esp32`
**Input:** "ESP32-WROOM-32 WiFi Module"
**Expected result:** Part numbers contain "ESP32"
**Actual result:** PASS

### TC-13 — Extract STM32 part number

**Script:** `tests/test_grabber.py::TestExtractPartNumbers::test_stm32`
**Input:** "STM32F429 Development Board"
**Expected result:** Part numbers contain "STM32F429"
**Actual result:** PASS

### TC-14 — Extract diode part number

**Script:** `tests/test_grabber.py::TestExtractPartNumbers::test_diode`
**Input:** "100pcs 1N4007 Rectifier Diode"
**Expected result:** Part numbers contain "1N4007"
**Actual result:** PASS

### TC-15 — Extract NE555 part number

**Script:** `tests/test_grabber.py::TestExtractPartNumbers::test_ne555`
**Input:** "10pcs NE555P Timer IC DIP-8"
**Expected result:** Part numbers contain "NE555"
**Actual result:** PASS

### TC-16 — Extract ATmega part number

**Script:** `tests/test_grabber.py::TestExtractPartNumbers::test_atmega`
**Input:** "ATmega2560 Mega Board"
**Expected result:** Part numbers contain "ATMEGA2560"
**Actual result:** PASS

### TC-17 — No parts from generic title

**Script:** `tests/test_grabber.py::TestExtractPartNumbers::test_no_parts`
**Input:** "USB Cable Type C Fast Charging"
**Expected result:** Empty list
**Actual result:** PASS

### TC-18 — Extract PCF8574 part number

**Script:** `tests/test_grabber.py::TestExtractPartNumbers::test_pcf8574`
**Input:** "PCF8574 I2C IO Expander Module"
**Expected result:** Part numbers contain "PCF8574"
**Actual result:** PASS

### TC-19 — Extract WS2812 part number

**Script:** `tests/test_grabber.py::TestExtractPartNumbers::test_ws2812`
**Input:** "60LEDs/m WS2812B RGB LED Strip"
**Expected result:** Part numbers contain "WS2812"
**Actual result:** PASS

### TC-20 — PNG to PDF conversion creates file

**Script:** `tests/test_grabber.py::TestConvertPngToPdf::test_creates_pdf_from_png`
**Input:** A 100x100 red PNG image
**Expected result:** PDF file created at specified path
**Actual result:** PASS

### TC-21 — PNG to PDF returns None on missing file

**Script:** `tests/test_grabber.py::TestConvertPngToPdf::test_returns_none_on_missing_png`
**Input:** Non-existent PNG path
**Expected result:** Returns None
**Actual result:** PASS

---

## Regression

All 57 pre-existing tests continue to pass (EUR conversion, date parsing, categorization, order parsing, PDF/MD generation, Octopart report, run report).

## Live Verification

Full rerun on 1071 orders: **1071 PDFs generated, 0 screenshots, 0 failures** (100% success rate).
