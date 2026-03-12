"""Shared constants, paths, keywords and component database.

Central configuration module — all other modules import constants from here
so that paths and keyword lists stay in sync.
"""

import os
from pathlib import Path
from urllib.parse import quote_plus

# ---------------------------------------------------------------------------
# Paths (anchored to the repository root, not the current working directory)
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INVOICES_DIR = SCRIPT_DIR / "invoices"
ANALYSIS_DIR = SCRIPT_DIR / "analysis"
ELECTRONICS_DIR = ANALYSIS_DIR / "electronics"
OUTPUT_CSV = SCRIPT_DIR / "orders_summary.csv"

# ---------------------------------------------------------------------------
# AliExpress URLs
# ---------------------------------------------------------------------------

ALIEXPRESS_ORDER_LIST_URL = "https://www.aliexpress.com/p/order/index.html"
ALIEXPRESS_ORDER_DETAIL_URL = (
    "https://www.aliexpress.com/p/order/detail.html?orderId={order_id}"
)
ALIEXPRESS_TAX_UI_URL = (
    "https://www.aliexpress.com/p/tax-ui/index.html"
    "?isGrayMatch=true&orderId={order_id}"
)

# Octopart component search URL
OCTOPART_SEARCH_URL = "https://octopart.com/search?q={query}"

# Parallel download workers (headed browser instances)
MAX_WORKERS = 2

# ---------------------------------------------------------------------------
# ECB exchange-rate feed
# ---------------------------------------------------------------------------

ECB_RATES_URL = (
    "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
)
ECB_NS = {
    "gesmes": "http://www.gesmes.org/xml/2002-08-01",
    "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
}

# ---------------------------------------------------------------------------
# Tesseract OCR path
# ---------------------------------------------------------------------------

TESSERACT_CMD = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Programs", "Tesseract-OCR", "tesseract.exe",
)

# ---------------------------------------------------------------------------
# Electronics keywords  (matched with word-boundary regex \b)
# ---------------------------------------------------------------------------

ELECTRONICS_KEYWORDS = [
    # PCB / board types
    "pcb", "circuit board", "dev board", "development board",
    "breakout board", "prototype board",
    # Passive components
    "resistor", "capacitor", "inductor", "diode", "ferrite",
    # Active / semiconductor
    "transistor", "mosfet", "igbt", "ic", "chip", "microcontroller",
    "mcu", "semiconductor", "op-amp", "opamp", "comparator",
    "fpga", "cpld", "eeprom",
    # Dev boards
    "arduino", "esp32", "esp8266", "stm32", "raspberry pi",
    # Sensors & modules
    "sensor", "relay", "gyroscope", "accelerometer",
    # Motors — compound forms only to avoid "motorcycle"
    "servo motor", "stepper motor", "dc motor", "bldc motor",
    "brushless motor", "gear motor", "servo", "stepper",
    "motor driver", "esc", "hyesc",
    # Power
    "transformer", "voltage regulator", "power supply",
    "buck converter", "boost converter", "dc-dc",
    "lipo", "li-ion", "18650",
    # Connectors / wiring
    "dupont", "breadboard", "jumper wire", "pin header",
    "jst connector", "xt60", "xt30",
    # Soldering & tools
    "soldering", "solder", "flux", "multimeter", "oscilloscope",
    "logic analyzer", "programmer", "debugger",
    "voltmeter", "ammeter", "wattmeter", "clamp meter",
    "crimping tool", "ferrule", "shrink tube", "heat shrink",
    # Displays
    "oled", "lcd", "tft",
    # Protocols / interfaces
    "uart", "spi", "i2c",
    # Wireless
    "antenna", "bluetooth module", "wifi module", "lora",
    # Thermal
    "heat sink", "heatsink",
    # Fabrication
    "3d print", "cnc machine", "cnc router", "laser engraver",
    # General electronics terms
    "electronic component", "electronic module", "electronic kit",
    "led strip", "led module", "ws2812", "neopixel",
    "potentiometer", "rotary encoder",
    # Packages
    "smd", "through hole", "dip", "sop", "qfp", "bga",
    # Specific chip references
    "555 timer", "ne555", "lm7805", "lm317",
]

# ---------------------------------------------------------------------------
# Automotive keywords
# ---------------------------------------------------------------------------

AUTOMOTIVE_KEYWORDS = [
    # Vehicle types
    "motorcycle", "motorbike", "dirt bike", "pit bike",
    "scooter", "atv", "quad",
    # Car diagnostics
    "obd", "obd2", "obdii", "diagnostic",
    "hex v2", "hex-v2", "vag", "inpa", "dcan",
    "enet", "openport", "ecu flash", "j2534",
    "opcom", "elm327",
    # Vehicle-specific parts
    "carburetor", "exhaust", "clutch", "throttle",
    "fuel sensor", "flex fuel", "o2 sensor", "oxygen sensor",
    "lambda", "starter relay", "solenoid",
    "fork", "handlebar", "pedal", "crankset",
    "bottom bracket", "derailleur", "chainring",
    # Vehicle brands / contexts
    "honda", "yamaha", "kawasaki", "suzuki",
    "bmw", "moto guzzi", "buick", "cadillac",
    "lifan", "zongshen", "loncin",
]

# ---------------------------------------------------------------------------
# Part number extraction patterns (regex)
# ---------------------------------------------------------------------------

PART_NUMBER_PATTERNS = [
    # Chip families
    r"\b(ESP32[A-Z0-9-]*)\b",
    r"\b(ESP8266[A-Z0-9-]*)\b",
    r"\b(STM32[A-Z0-9]+)\b",
    r"\b(ATmega[0-9A-Z]+)\b",
    r"\b(AT[0-9]{2}[A-Z][0-9A-Z]+)\b",
    r"\b(PIC[0-9]+[A-Z0-9]*)\b",
    r"\b(CH32[A-Z0-9]+)\b",
    r"\b(RP2040)\b",
    # Discrete semiconductors
    r"\b([12]N[0-9]{3,5}[A-Z]?)\b",
    r"\b(BC[0-9]{3}[A-Z]?)\b",
    r"\b(IRF[0-9]+[A-Z]*)\b",
    # ICs
    r"\b(NE555[A-Z]*)\b",
    r"\b(LM[0-9]{3,5}[A-Z]*)\b",
    r"\b(SN[0-9]+[A-Z0-9]+)\b",
    r"\b(74[HCL][A-Z]*[0-9]+)\b",
    r"\b(ULN200[0-9])\b",
    # Connectors
    r"\b(JST-?[A-Z]+)\b",
    r"\b(XT[0-9]{2})\b",
    # Displays
    r"\b(SSD[0-9]{4})\b",
    r"\b(ILI[0-9]{4})\b",
    r"\b(ST77[0-9]{2})\b",
    # Wireless
    r"\b(NRF[0-9A-Z]+)\b",
    r"\b(CC[0-9]{4})\b",
    # Sensors
    r"\b(MPU[0-9]+)\b",
    r"\b(BMP[0-9]+)\b",
    r"\b(DHT[0-9]+)\b",
    r"\b(ACS[0-9]+)\b",
    # Packages with part refs
    r"\b(MEGA[0-9]+)\b",
    r"\b(A22[0-9]{2})\b",
    # LED chips
    r"\b(WS28[0-9]+[A-Z]*)\b",
    r"\b(SK68[0-9]+)\b",
    # Modules
    r"\b(PCF[0-9]{4}[A-Z]*)\b",
    r"\b(ADS[0-9]{4})\b",
    r"\b(MCP[0-9]{4})\b",
    # Motor drivers
    r"\b(L298[A-Z]?)\b",
    r"\b(A4988)\b",
    r"\b(TMC[0-9]{4})\b",
    r"\b(DRV[0-9]+)\b",
    # Power
    r"\b(LM25[0-9]{2})\b",
    r"\b(XL[0-9]{4})\b",
    # WiFi/BT modules
    r"\b(QC[A-Z]*[0-9]{3,})\b",
]

# ---------------------------------------------------------------------------
# Curated component database
# ---------------------------------------------------------------------------

PART_DATABASE = {
    # Microcontrollers / SoCs
    "ESP32": {"manufacturer": "Espressif", "description": "WiFi + Bluetooth SoC, dual-core Xtensa LX6"},
    "ESP8266": {"manufacturer": "Espressif", "description": "WiFi SoC, single-core Tensilica L106"},
    "STM32F103": {"manufacturer": "STMicroelectronics", "description": "ARM Cortex-M3 MCU, 72 MHz"},
    "STM32F401": {"manufacturer": "STMicroelectronics", "description": "ARM Cortex-M4 MCU, 84 MHz"},
    "STM32F407": {"manufacturer": "STMicroelectronics", "description": "ARM Cortex-M4 MCU, 168 MHz"},
    "STM32F411": {"manufacturer": "STMicroelectronics", "description": "ARM Cortex-M4 MCU, 100 MHz"},
    "STM32F429": {"manufacturer": "STMicroelectronics", "description": "ARM Cortex-M4 MCU, 180 MHz, LCD-TFT"},
    "STM32F030": {"manufacturer": "STMicroelectronics", "description": "ARM Cortex-M0 MCU, 48 MHz"},
    "ATMEGA328P": {"manufacturer": "Microchip", "description": "8-bit AVR MCU, 20 MHz (Arduino Uno)"},
    "ATMEGA328": {"manufacturer": "Microchip", "description": "8-bit AVR MCU, 20 MHz"},
    "ATMEGA2560": {"manufacturer": "Microchip", "description": "8-bit AVR MCU, 16 MHz (Arduino Mega)"},
    "ATMEGA8": {"manufacturer": "Microchip", "description": "8-bit AVR MCU, 16 MHz"},
    "ATMEGA128": {"manufacturer": "Microchip", "description": "8-bit AVR MCU, 16 MHz, 128 KB Flash"},
    "ATTINY85": {"manufacturer": "Microchip", "description": "8-bit AVR MCU, 20 MHz, 8 KB Flash"},
    "ATTINY13": {"manufacturer": "Microchip", "description": "8-bit AVR MCU, 20 MHz, 1 KB Flash"},
    "PIC16F877": {"manufacturer": "Microchip", "description": "8-bit PIC MCU, 20 MHz"},
    "RP2040": {"manufacturer": "Raspberry Pi", "description": "Dual-core ARM Cortex-M0+, 133 MHz"},
    "CH340": {"manufacturer": "WCH", "description": "USB to UART bridge IC"},
    "CH340G": {"manufacturer": "WCH", "description": "USB to UART bridge IC"},
    "CH32V003": {"manufacturer": "WCH", "description": "RISC-V MCU, 48 MHz"},
    # Discrete semiconductors
    "1N4001": {"manufacturer": "Various", "description": "1A 50V rectifier diode, DO-41"},
    "1N4004": {"manufacturer": "Various", "description": "1A 400V rectifier diode, DO-41"},
    "1N4007": {"manufacturer": "Various", "description": "1A 1000V rectifier diode, DO-41"},
    "1N4148": {"manufacturer": "Various", "description": "Small signal switching diode, DO-35"},
    "1N5408": {"manufacturer": "Various", "description": "3A 1000V rectifier diode, DO-201"},
    "1N5817": {"manufacturer": "Various", "description": "1A 20V Schottky diode, DO-41"},
    "1N5822": {"manufacturer": "Various", "description": "3A 40V Schottky diode, DO-201"},
    "2N2222": {"manufacturer": "Various", "description": "NPN general purpose transistor, TO-92"},
    "2N7000": {"manufacturer": "Various", "description": "N-channel MOSFET, 60V 200mA, TO-92"},
    "BC547": {"manufacturer": "Various", "description": "NPN general purpose transistor, TO-92"},
    "IRFZ44N": {"manufacturer": "Various", "description": "N-channel MOSFET, 55V 49A, TO-220"},
    "IRF540": {"manufacturer": "Various", "description": "N-channel MOSFET, 100V 33A, TO-220"},
    # ICs
    "NE555": {"manufacturer": "Texas Instruments", "description": "Precision timer IC, DIP-8"},
    "NE555P": {"manufacturer": "Texas Instruments", "description": "Precision timer IC, DIP-8"},
    "LM7805": {"manufacturer": "Various", "description": "5V 1A linear voltage regulator, TO-220"},
    "LM317": {"manufacturer": "Various", "description": "Adjustable voltage regulator, 1.2-37V"},
    "LM2596": {"manufacturer": "Texas Instruments", "description": "3A step-down voltage regulator"},
    "LM393": {"manufacturer": "Various", "description": "Dual differential comparator, DIP-8"},
    "ULN2003": {"manufacturer": "Various", "description": "7-channel Darlington transistor array"},
    "74HC595": {"manufacturer": "Various", "description": "8-bit shift register, output latch"},
    "74HC245": {"manufacturer": "Various", "description": "Octal bus transceiver, 3-state"},
    # Sensors / modules
    "MPU6050": {"manufacturer": "InvenSense", "description": "6-axis accelerometer + gyroscope, I2C"},
    "BMP280": {"manufacturer": "Bosch", "description": "Barometric pressure + temperature sensor"},
    "BME280": {"manufacturer": "Bosch", "description": "Pressure + humidity + temperature sensor"},
    "DHT11": {"manufacturer": "Aosong", "description": "Temperature + humidity sensor, digital"},
    "DHT22": {"manufacturer": "Aosong", "description": "Temperature + humidity sensor, digital"},
    "ACS712": {"manufacturer": "Allegro", "description": "Hall-effect current sensor, ±5-30A"},
    "DS18B20": {"manufacturer": "Maxim", "description": "1-Wire digital temperature sensor"},
    "SSD1306": {"manufacturer": "Solomon Systech", "description": "128x64 OLED display driver, I2C/SPI"},
    "ILI9341": {"manufacturer": "Ilitek", "description": "240x320 TFT LCD driver, SPI"},
    "ST7735": {"manufacturer": "Sitronix", "description": "128x160 TFT LCD driver, SPI"},
    "ST7789": {"manufacturer": "Sitronix", "description": "240x320/240 TFT LCD driver, SPI"},
    "PCF8574": {"manufacturer": "NXP", "description": "8-bit I/O expander, I2C"},
    "ADS1115": {"manufacturer": "Texas Instruments", "description": "16-bit ADC, 4-channel, I2C"},
    "MCP2515": {"manufacturer": "Microchip", "description": "CAN bus controller, SPI"},
    # Wireless
    "NRF24L01": {"manufacturer": "Nordic", "description": "2.4 GHz transceiver, SPI"},
    "CC1101": {"manufacturer": "Texas Instruments", "description": "Sub-1 GHz transceiver"},
    "SX1278": {"manufacturer": "Semtech", "description": "LoRa transceiver, 137-525 MHz"},
    # Motor drivers
    "L298N": {"manufacturer": "STMicroelectronics", "description": "Dual H-bridge motor driver"},
    "A4988": {"manufacturer": "Allegro", "description": "Stepper motor driver, microstepping"},
    "TMC2209": {"manufacturer": "Trinamic", "description": "Stepper motor driver, UART, StealthChop"},
    "DRV8825": {"manufacturer": "Texas Instruments", "description": "Stepper motor driver, 1/32 step"},
    # LEDs
    "WS2812": {"manufacturer": "Worldsemi", "description": "Addressable RGB LED, 5050 package"},
    "WS2812B": {"manufacturer": "Worldsemi", "description": "Addressable RGB LED, 5050 package"},
    "SK6812": {"manufacturer": "Various", "description": "Addressable RGBW LED, 5050 package"},
    # Connectors
    "XT60": {"manufacturer": "Amass", "description": "High-current DC connector, 60A rated"},
    "XT30": {"manufacturer": "Amass", "description": "High-current DC connector, 30A rated"},
    # Power
    "XL6009": {"manufacturer": "XLSEMI", "description": "4A DC-DC boost converter IC"},
    "XL6019": {"manufacturer": "XLSEMI", "description": "5A DC-DC boost converter IC"},
}


def octopart_search_url(query):
    """Generate an Octopart search URL for a component query.

    Args:
        query: Component name or description to search for.

    Returns:
        Octopart search URL string.
    """
    return OCTOPART_SEARCH_URL.format(query=quote_plus(query))
