"""Unit tests for the AliExpress grabber — pure logic functions.

Tests EUR conversion, date parsing, order categorization, and raw order parsing.
All tests are offline — no browser or network required.
"""

import math

import pytest

# Import functions under test by manipulating the path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grabber import (
    categorize_order,
    convert_png_to_pdf,
    extract_part_numbers,
    generate_invoice_md,
    generate_invoice_pdf,
    generate_octopart_report,
    generate_order_summary,
    generate_run_report,
    generate_yearly_summary,
    octopart_search_url,
    parse_aliexpress_date,
    parse_raw_order,
    usd_to_eur_rounded_up,
)


# ---------------------------------------------------------------------------
# ECB rate fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ecb_rates():
    """Minimal ECB rate table for testing."""
    return {
        "2025-01-13": 1.0250,  # Monday
        "2025-01-14": 1.0300,  # Tuesday
        "2025-01-15": 1.0280,  # Wednesday
        "2025-01-10": 1.0200,  # Friday (before weekend)
        "2024-12-31": 1.0400,  # New Year's Eve
        "2024-12-30": 1.0380,  # Monday
    }


# ---------------------------------------------------------------------------
# EUR Conversion tests
# ---------------------------------------------------------------------------

class TestUsdToEurRoundedUp:
    """Test USD to EUR conversion with rounding up."""

    def test_exact_date_match(self, ecb_rates):
        """Rate on a known business day."""
        eur, rate, date_used = usd_to_eur_rounded_up(10.30, "2025-01-14", ecb_rates)
        assert rate == 1.0300
        assert date_used == "2025-01-14"
        expected = math.ceil(10.30 / 1.0300 * 100) / 100
        assert eur == expected

    def test_weekend_falls_back_to_friday(self, ecb_rates):
        """Saturday/Sunday should use Friday's rate."""
        eur, rate, date_used = usd_to_eur_rounded_up(5.00, "2025-01-11", ecb_rates)
        assert date_used == "2025-01-10"
        assert rate == 1.0200

    def test_sunday_falls_back_to_friday(self, ecb_rates):
        """Sunday should also fall back to Friday."""
        eur, rate, date_used = usd_to_eur_rounded_up(5.00, "2025-01-12", ecb_rates)
        assert date_used == "2025-01-10"

    def test_rounds_up_not_down(self, ecb_rates):
        """Verify rounding is always up (ceiling)."""
        # 10.00 / 1.025 = 9.75609... → must round up to 9.76, not 9.75
        eur, _, _ = usd_to_eur_rounded_up(10.00, "2025-01-13", ecb_rates)
        assert eur == math.ceil(10.00 / 1.0250 * 100) / 100
        assert eur >= 10.00 / 1.0250  # Must be >= exact value

    def test_zero_price(self, ecb_rates):
        """Zero USD should convert to zero EUR."""
        eur, _, _ = usd_to_eur_rounded_up(0.0, "2025-01-14", ecb_rates)
        assert eur == 0.0

    def test_large_amount(self, ecb_rates):
        """Large amounts should still round up correctly."""
        eur, _, _ = usd_to_eur_rounded_up(999.99, "2025-01-14", ecb_rates)
        expected = math.ceil(999.99 / 1.0300 * 100) / 100
        assert eur == expected

    def test_fallback_to_most_recent_rate(self, ecb_rates):
        """Date far from any known rate uses the most recent one."""
        eur, rate, date_used = usd_to_eur_rounded_up(10.00, "2025-06-01", ecb_rates)
        # Should fall back to most recent rate in the dict
        assert date_used == "2025-01-15"

    def test_empty_rates_returns_one_to_one(self):
        """Empty rate dict should return 1:1 conversion."""
        eur, rate, date_used = usd_to_eur_rounded_up(10.00, "2025-01-14", {})
        assert eur == 10.00
        assert rate == 1.0


# ---------------------------------------------------------------------------
# Date parsing tests
# ---------------------------------------------------------------------------

class TestParseAliexpressDate:
    """Test parsing various AliExpress date formats."""

    def test_us_format(self):
        assert parse_aliexpress_date("Jan 15, 2025") == "2025-01-15"

    def test_us_format_full_month(self):
        assert parse_aliexpress_date("January 15, 2025") == "2025-01-15"

    def test_iso_format(self):
        assert parse_aliexpress_date("2025-01-15") == "2025-01-15"

    def test_european_dot_format(self):
        assert parse_aliexpress_date("15.01.2025") == "2025-01-15"

    def test_european_slash_format(self):
        assert parse_aliexpress_date("15/01/2025") == "2025-01-15"

    def test_with_prefix_order_date(self):
        assert parse_aliexpress_date("Order date: Jan 15, 2025") == "2025-01-15"

    def test_with_prefix_paid_on(self):
        assert parse_aliexpress_date("Paid on Jan 15, 2025") == "2025-01-15"

    def test_day_month_year_spaces(self):
        assert parse_aliexpress_date("15 Jan 2025") == "2025-01-15"

    def test_empty_string_returns_empty(self):
        result = parse_aliexpress_date("")
        assert result == ""

    def test_garbage_returns_as_is(self):
        result = parse_aliexpress_date("not a date")
        assert result == "not a date"

    def test_iso_with_dots(self):
        assert parse_aliexpress_date("2025.01.15") == "2025-01-15"


# ---------------------------------------------------------------------------
# Categorization tests
# ---------------------------------------------------------------------------

class TestCategorizeOrder:
    """Test order categorization as Electronics vs Other."""

    def test_resistor_is_electronics(self):
        assert categorize_order(["100pcs 10K Resistor 0805"]) == "Electronics"

    def test_arduino_is_electronics(self):
        assert categorize_order(["Arduino Nano V3.0 ATmega328"]) == "Electronics"

    def test_esp32_is_electronics(self):
        assert categorize_order(["ESP32 Development Board WiFi"]) == "Electronics"

    def test_multimeter_is_electronics(self):
        assert categorize_order(["Digital Multimeter Auto Range"]) == "Electronics"

    def test_soldering_iron_is_electronics(self):
        assert categorize_order(["Soldering Iron 60W Kit"]) == "Electronics"

    def test_clothing_is_other(self):
        assert categorize_order(["Men's Winter Jacket Warm"]) == "Other"

    def test_kitchen_is_other(self):
        assert categorize_order(["Stainless Steel Cooking Pot"]) == "Other"

    def test_phone_case_is_other(self):
        assert categorize_order(["Silicone Phone Case Protective"]) == "Other"

    def test_mixed_order_electronics_wins(self):
        """If any item is electronics, entire order is Electronics."""
        items = ["Phone Case Cover", "ESP32 Dev Board WiFi", "Screen Protector"]
        assert categorize_order(items) == "Electronics"

    def test_empty_items_is_other(self):
        assert categorize_order([]) == "Other"

    def test_case_insensitive(self):
        assert categorize_order(["CAPACITOR 100uF"]) == "Electronics"

    def test_servo_motor_is_electronics(self):
        assert categorize_order(["MG996R Servo Motor 180 Degree"]) == "Electronics"

    def test_3d_print_is_electronics(self):
        assert categorize_order(["3D Print PLA Filament 1kg"]) == "Electronics"

    def test_motorcycle_is_not_electronics(self):
        """Motorcycle brake pads must NOT match — 'motor' != 'motorcycle'."""
        assert categorize_order(["Motorcycle Front Rear Brake Disc Pads"]) == "Other"

    def test_stepper_motor_is_electronics(self):
        assert categorize_order(["Nema 17 Stepper Motor 42mm"]) == "Electronics"

    def test_servo_alone_is_electronics(self):
        assert categorize_order(["25KG Digital Servo Waterproof"]) == "Electronics"

    def test_oled_display_is_electronics(self):
        assert categorize_order(["0.96 inch OLED Display Module"]) == "Electronics"

    def test_esc_is_electronics(self):
        """ESC (electronic speed controller) should match."""
        assert categorize_order(["BLHeli 30A ESC Speed Controller"]) == "Electronics"


# ---------------------------------------------------------------------------
# Raw order parsing tests
# ---------------------------------------------------------------------------

class TestParseRawOrder:
    """Test parsing raw order data into standardized format."""

    def test_normal_order(self):
        raw = {
            "order_id": "8123456789",
            "date": "Jan 15, 2025",
            "total_text": "$12.50",
            "items": ["ESP32 Dev Board"],
        }
        result = parse_raw_order(raw)
        assert result["order_id"] == "8123456789"
        assert result["date"] == "2025-01-15"
        assert result["total_usd"] == 12.50
        assert result["items"] == ["ESP32 Dev Board"]

    def test_price_with_comma(self):
        raw = {
            "order_id": "100",
            "date": "2025-01-15",
            "total_text": "US $1,234.56",
            "items": [],
        }
        result = parse_raw_order(raw)
        assert result["total_usd"] == 1234.56

    def test_missing_price(self):
        raw = {
            "order_id": "200",
            "date": "2025-01-15",
            "total_text": "",
            "items": [],
        }
        result = parse_raw_order(raw)
        assert result["total_usd"] == 0.0

    def test_missing_date(self):
        raw = {
            "order_id": "300",
            "date": "",
            "total_text": "$5.00",
            "items": ["Test Item"],
        }
        result = parse_raw_order(raw)
        assert result["date"] == ""

    def test_euro_price_format(self):
        raw = {
            "order_id": "400",
            "date": "2025-01-15",
            "total_text": "€9.99",
            "items": [],
        }
        result = parse_raw_order(raw)
        assert result["total_usd"] == 9.99


# ---------------------------------------------------------------------------
# PDF generation tests
# ---------------------------------------------------------------------------

class TestGenerateInvoicePdf:
    """Test PDF generation from receipt data."""

    def test_creates_pdf_file(self, tmp_path):
        receipt = {
            "order_id": "123456",
            "order_time": "2025-01-15 10:30",
            "items": [{"title": "Test Widget", "price": "$9.99", "quantity": "2"}],
            "subtotal": "$19.98",
            "discount": "$0.00",
            "shipping": "$0.00",
            "total": "$19.98",
            "vat": "$3.20",
            "address_lines": ["John Doe", "123 Main St", "Berlin, Germany"],
            "payment_method": "Credit card ending 1234",
        }
        pdf_path = tmp_path / "test_invoice.pdf"
        generate_invoice_pdf(receipt, pdf_path)
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0

    def test_creates_parent_directories(self, tmp_path):
        receipt = {
            "order_id": "789",
            "order_time": "2025-03-01",
            "items": [],
            "subtotal": "$5.00",
            "total": "$5.00",
        }
        pdf_path = tmp_path / "nested" / "dir" / "invoice.pdf"
        generate_invoice_pdf(receipt, pdf_path)
        assert pdf_path.exists()

    def test_handles_empty_items(self, tmp_path):
        receipt = {
            "order_id": "999",
            "items": [],
            "total": "$0.00",
        }
        pdf_path = tmp_path / "empty.pdf"
        generate_invoice_pdf(receipt, pdf_path)
        assert pdf_path.exists()


# ---------------------------------------------------------------------------
# Markdown invoice tests
# ---------------------------------------------------------------------------

class TestGenerateInvoiceMd:
    """Test per-order Markdown invoice generation."""

    def test_creates_md_file(self, tmp_path, ecb_rates):
        receipt = {
            "order_id": "123456",
            "order_time": "2025-01-15",
            "items": [{"title": "ESP32 Board", "price": "$12.50", "quantity": "1"}],
            "subtotal": "$12.50",
            "total": "$12.50",
            "vat": "$2.00",
        }
        order = {
            "order_id": "123456",
            "date": "2025-01-15",
            "items": ["ESP32 Board"],
            "total_usd": 12.50,
            "category": "Electronics",
        }
        md_path = tmp_path / "inv.md"
        generate_invoice_md(receipt, order, md_path, ecb_rates)
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "123456" in content
        assert "ESP32 Board" in content
        assert "Electronics" in content
        assert "EUR" in content

    def test_electronics_md_has_octopart_links(self, tmp_path, ecb_rates):
        receipt = {
            "order_id": "777",
            "items": [{"title": "Arduino Nano", "price": "$5.00", "quantity": "1"}],
            "total": "$5.00",
        }
        order = {
            "order_id": "777",
            "date": "2025-01-15",
            "items": ["Arduino Nano"],
            "total_usd": 5.00,
            "category": "Electronics",
        }
        md_path = tmp_path / "elec.md"
        generate_invoice_md(receipt, order, md_path, ecb_rates)
        content = md_path.read_text(encoding="utf-8")
        assert "Component Identification" in content
        assert "octopart.com/search" in content
        assert "Arduino Nano" in content

    def test_without_receipt_data(self, tmp_path, ecb_rates):
        order = {
            "order_id": "9999",
            "date": "2025-01-14",
            "items": ["Some Item"],
            "total_usd": 5.00,
            "category": "Other",
        }
        md_path = tmp_path / "fallback.md"
        generate_invoice_md(None, order, md_path, ecb_rates)
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "9999" in content
        assert "$5.00" in content


# ---------------------------------------------------------------------------
# Yearly summary tests
# ---------------------------------------------------------------------------

class TestGenerateYearlySummary:
    """Test yearly summary generation."""

    def test_creates_summary_file(self, tmp_path, ecb_rates):
        orders = [
            {"order_id": "1", "date": "2025-01-13", "items": ["Arduino"], "total_usd": 10.0, "category": "Electronics"},
            {"order_id": "2", "date": "2025-01-14", "items": ["T-Shirt"], "total_usd": 5.0, "category": "Other"},
        ]
        generate_yearly_summary("2025", orders, ecb_rates, tmp_path)
        summary = tmp_path / "2025_summary.md"
        assert summary.exists()
        content = summary.read_text(encoding="utf-8")
        assert "2025" in content
        assert "Electronics" in content
        assert "Other" in content
        assert "Grand Total" in content


# ---------------------------------------------------------------------------
# Order summary tests
# ---------------------------------------------------------------------------

class TestGenerateOrderSummary:
    """Test overall order summary generation."""

    def test_creates_summary_file(self, tmp_path, ecb_rates):
        orders = [
            {"order_id": "1", "date": "2025-01-13", "items": ["Arduino"], "total_usd": 10.0, "category": "Electronics"},
            {"order_id": "2", "date": "2024-12-31", "items": ["Hat"], "total_usd": 3.0, "category": "Other"},
        ]
        summary_path = tmp_path / "summary.md"
        generate_order_summary(orders, ecb_rates, summary_path)
        assert summary_path.exists()
        content = summary_path.read_text(encoding="utf-8")
        assert "AliExpress Order Summary" in content
        assert "2025" in content
        assert "2024" in content
        assert "Arduino" in content


# ---------------------------------------------------------------------------
# Octopart search tests
# ---------------------------------------------------------------------------

class TestOctopartSearchUrl:
    """Test Octopart search URL generation."""

    def test_simple_query(self):
        url = octopart_search_url("ESP32")
        assert url == "https://octopart.com/search?q=ESP32"

    def test_spaces_encoded(self):
        url = octopart_search_url("Arduino Nano V3")
        assert "Arduino+Nano+V3" in url or "Arduino%20Nano%20V3" in url

    def test_special_characters_encoded(self):
        url = octopart_search_url("100µF Capacitor 16V")
        assert "octopart.com/search?q=" in url


class TestGenerateOctopartReport:
    """Test Octopart search report generation."""

    def test_creates_report_for_electronics(self, tmp_path):
        orders = [
            {"order_id": "1", "date": "2025-01-13", "items": ["Arduino Nano"], "total_usd": 10.0, "category": "Electronics"},
            {"order_id": "2", "date": "2025-01-14", "items": ["T-Shirt"], "total_usd": 5.0, "category": "Other"},
        ]
        report_path = tmp_path / "octopart.md"
        generate_octopart_report(orders, report_path)
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "Octopart" in content
        assert "Arduino Nano" in content
        assert "T-Shirt" not in content

    def test_skips_when_no_electronics(self, tmp_path):
        orders = [
            {"order_id": "1", "date": "2025-01-13", "items": ["Hat"], "total_usd": 3.0, "category": "Other"},
        ]
        report_path = tmp_path / "octopart.md"
        generate_octopart_report(orders, report_path)
        assert not report_path.exists()

    def test_contains_search_links(self, tmp_path):
        orders = [
            {"order_id": "1", "date": "2025-01-13", "items": ["ESP32 Dev Board", "10K Resistor"], "total_usd": 15.0, "category": "Electronics"},
        ]
        report_path = tmp_path / "octopart.md"
        generate_octopart_report(orders, report_path)
        content = report_path.read_text(encoding="utf-8")
        assert "octopart.com/search" in content
        assert "ESP32" in content
        assert "Resistor" in content


# ---------------------------------------------------------------------------
# Run Report tests
# ---------------------------------------------------------------------------

class TestGenerateRunReport:
    """Test run report generation."""

    def test_creates_report_with_status(self, tmp_path, monkeypatch):
        monkeypatch.setattr("grabber.SCRIPT_DIR", tmp_path)
        orders = [
            {"order_id": "111", "date": "2025-01-13", "items": ["Widget"], "total_usd": 5.0, "category": "Other"},
            {"order_id": "222", "date": "2025-02-10", "items": ["Gadget"], "total_usd": 10.0, "category": "Electronics"},
            {"order_id": "333", "date": "2026-01-05", "items": ["Thing"], "total_usd": 3.0, "category": "Other"},
        ]
        download_paths = {
            "111": tmp_path / "invoices" / "2025" / "2025-01-13-111.pdf",
            "222": tmp_path / "invoices" / "2025" / "2025-02-10-222.png",
            "333": None,
        }
        ecb_rates = {"2025-01-13": 1.03, "2026-01-05": 1.05}
        generate_run_report(orders, download_paths, ecb_rates)
        report = (tmp_path / "run_report.md").read_text(encoding="utf-8")
        assert "PDF Invoices:** 1" in report
        assert "Screenshot Fallbacks:** 1" in report
        assert "Failed Downloads:** 1" in report
        assert "✓ PDF" in report
        assert "📷 Screenshot" in report
        assert "✗ Failed" in report
        assert "2025" in report
        assert "2026" in report


# ---------------------------------------------------------------------------
# Automotive exclusion tests
# ---------------------------------------------------------------------------

class TestAutomotiveExclusion:
    """Test that automotive/motorcycle items are not classified as Electronics."""

    def test_motorcycle_cnc_part_is_other(self):
        assert categorize_order(["CNC Aluminum Motorcycle Brake Handle"]) == "Other"

    def test_car_diagnostic_hex_v2_is_other(self):
        assert categorize_order(["Real ARM STM32F429 Chip For VAG HEX V2"]) == "Other"

    def test_obd_scanner_is_other(self):
        assert categorize_order(["ELM327 Mini V2.1 Bluetooth OBD2 Diagnostic"]) == "Other"

    def test_flex_fuel_sensor_is_other(self):
        assert categorize_order(["Flex Fuel Sensor for Buick Cadillac"]) == "Other"

    def test_o2_sensor_is_other(self):
        assert categorize_order(["O2 Oxygen Sensor for Honda CRF"]) == "Other"

    def test_starter_relay_motorcycle_is_other(self):
        assert categorize_order(["Starter Relay Solenoid for Kawasaki ZX750"]) == "Other"

    def test_motorcycle_kill_switch_is_other(self):
        assert categorize_order(["Motorcycle CNC Billet Engine Stop Start Kill Switch"]) == "Other"

    def test_openport_ecu_flash_is_other(self):
        assert categorize_order(["Openport 2.0 ECU Flash J2534"]) == "Other"

    def test_pure_esp32_still_electronics(self):
        assert categorize_order(["ESP32 Development Board WiFi Module"]) == "Electronics"

    def test_pure_arduino_still_electronics(self):
        assert categorize_order(["Arduino Nano Every MEGA2560"]) == "Electronics"

    def test_pure_resistor_still_electronics(self):
        assert categorize_order(["100PCS 1N4001 1N4007 Diode Kit"]) == "Electronics"


# ---------------------------------------------------------------------------
# Part number extraction tests
# ---------------------------------------------------------------------------

class TestExtractPartNumbers:
    """Test electronic component part number extraction from titles."""

    def test_esp32(self):
        parts = extract_part_numbers("ESP32 C3 Development Board")
        assert "ESP32" in parts

    def test_stm32(self):
        parts = extract_part_numbers("STM32F429 Chip For VAG")
        assert "STM32F429" in parts

    def test_diode(self):
        parts = extract_part_numbers("100PCS 1N4001 1N4004 1N4007")
        assert "1N4001" in parts
        assert "1N4007" in parts

    def test_ne555(self):
        parts = extract_part_numbers("NE555 Timer IC Module")
        assert "NE555" in parts

    def test_atmega(self):
        parts = extract_part_numbers("MEGA2560 ATmega2560-16AU Board")
        assert "ATMEGA2560" in parts

    def test_no_parts(self):
        parts = extract_part_numbers("Generic Phone Case Cover")
        assert parts == []

    def test_pcf8574(self):
        parts = extract_part_numbers("LCD1602 I2C PCF8574 Module")
        assert "PCF8574" in parts

    def test_ws2812(self):
        parts = extract_part_numbers("WS2812B LED Strip Neopixel")
        assert "WS2812B" in parts


# ---------------------------------------------------------------------------
# PNG to PDF conversion tests
# ---------------------------------------------------------------------------

class TestConvertPngToPdf:
    """Test PNG screenshot to PDF conversion."""

    def test_creates_pdf_from_png(self, tmp_path):
        from PIL import Image
        png_path = tmp_path / "test.png"
        img = Image.new("RGB", (800, 1200), color=(255, 255, 255))
        img.save(str(png_path))

        pdf_path = tmp_path / "test.pdf"
        result = convert_png_to_pdf(png_path, pdf_path)
        assert result == pdf_path
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0

    def test_returns_none_on_missing_png(self, tmp_path):
        png_path = tmp_path / "missing.png"
        pdf_path = tmp_path / "out.pdf"
        result = convert_png_to_pdf(png_path, pdf_path)
        assert result is None
