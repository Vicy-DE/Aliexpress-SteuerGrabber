# Todo: Order Categorization

**Created:** 2026-03-09
**Requirement:** [Req #5 — Order Categorization](../Requirements/requirements.md)
**Status:** Done

---

## Tasks

- [x] Define comprehensive electronics keyword list
  - [x] Passive components (resistor, capacitor, inductor, diode, fuse)
  - [x] Active components (transistor, MOSFET, IC, MCU, FPGA, EEPROM)
  - [x] Dev boards (Arduino, ESP32, STM32, Raspberry)
  - [x] Test equipment (multimeter, oscilloscope, logic analyzer)
  - [x] Connectors, wiring, soldering supplies
  - [x] Power electronics (buck, boost, converter, battery, charger)
  - [x] Communication (UART, SPI, I2C, RF, Bluetooth, WiFi, LoRa)
  - [x] Displays (OLED, LCD, TFT)
  - [x] Mechanical (3D print, CNC, laser, heatsink, fan)
  - [x] Package types (SMD, DIP, SOP, QFP, BGA)
- [x] Case-insensitive keyword matching against concatenated item titles
- [x] Any single match → classify entire order as "Electronics"
- [x] Default to "Other" if no keywords match
- [x] Script runs without errors
- [x] CHANGE_LOG.md updated

---

## Notes

- The keyword list is intentionally broad to catch most electronics-related purchases.
- Edge cases: items like "LED desk lamp" or "USB cable for phone" will also match — manual review of the CSV may be needed for borderline cases.
