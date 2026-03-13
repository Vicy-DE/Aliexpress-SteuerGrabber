"""PDF invoice generation and OCR-based screenshot-to-PDF conversion.

Generates text-based PDF invoices from structured receipt data using fpdf2.
For fallback cases, embeds the original screenshot image into the PDF and
uses Tesseract OCR to extract text for verification against the
companion Markdown file.
"""

import os
import re
from pathlib import Path

from fpdf import FPDF

from utils.config import TESSERACT_CMD

# Unicode → latin-1 replacements for Helvetica
_REPLACEMENTS = {
    "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR",
    "…": "...", "\u2013": "-", "\u2014": "--",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
}


def _safe(text):
    """Encode text safely for Helvetica font.

    Args:
        text: Input string.

    Returns:
        Latin-1 safe string.
    """
    for char, repl in _REPLACEMENTS.items():
        text = text.replace(char, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


# -------------------------------------------------------------------
# Screenshot → PDF  (image-based, with optional OCR verification)
# -------------------------------------------------------------------

def convert_png_to_pdf(png_path, pdf_path, order=None, ecb_rates=None,
                        product_images=None, receipt_data=None):
    """Convert a PNG screenshot to a PDF embedding the original image.

    The PDF shows the same picture as the original screenshot.
    If *order* data is provided, a text page with order details is
    prepended (page 1) and the screenshot becomes page 2.

    Args:
        png_path: Path to the source PNG file.
        pdf_path: Path where the resulting PDF will be saved.
        order: Optional order dict with items, total_usd, date, order_id.
        ecb_rates: Optional ECB exchange rate dict for EUR conversion.
        product_images: Optional list of product image file paths.
        receipt_data: Optional dict with structured receipt data.

    Returns:
        Path to the created PDF, or None on failure.
    """
    try:
        from PIL import Image

        with Image.open(str(png_path)) as img:
            img_w, img_h = img.size

        pdf = FPDF()

        # Page 1 (optional): text invoice from order data
        if order:
            _add_text_page(
                pdf, order, ecb_rates=ecb_rates,
                product_images=product_images,
                receipt_data=receipt_data,
            )

        # Image page: embed the original screenshot
        page_w = 190
        scale = page_w / img_w
        page_h = img_h * scale
        pdf.add_page(format=(page_w + 20, page_h + 20))
        pdf.image(str(png_path), x=10, y=10, w=page_w)

        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(str(pdf_path))
        return pdf_path
    except Exception as exc:
        print(f"    PNG->PDF conversion failed: {exc}")
        return None


def _add_text_page(pdf, order, ecb_rates=None, product_images=None,
                   receipt_data=None):
    """Add a branded invoice page to the PDF with EUR and Octopart info.

    Args:
        pdf: FPDF instance.
        order: Order dict.
        ecb_rates: Optional ECB exchange rate dict.
        product_images: Optional list of product image file paths.
        receipt_data: Optional dict with structured receipt data.
    """
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # AliExpress branded header
    pdf.set_fill_color(232, 65, 24)
    pdf.rect(10, 10, 190, 16, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(15, 11)
    pdf.cell(0, 14, "AliExpress  Order Invoice", align="L")
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(30)

    # Order metadata
    pdf.set_font("Helvetica", "", 10)
    for label, key in [("Order ID:", "order_id"),
                       ("Date:", "date"),
                       ("Category:", "category")]:
        pdf.cell(40, 6, label, new_x="RIGHT")
        pdf.cell(
            0, 6, str(order.get(key, "Other" if key == "category" else "")),
            new_x="LMARGIN", new_y="NEXT",
        )

    # Price with EUR conversion
    total = order.get("total_usd", 0)
    if total:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 7, "Total (USD):", new_x="RIGHT")
        pdf.cell(0, 7, f"${total:.2f}", new_x="LMARGIN", new_y="NEXT")
        if ecb_rates and order.get("date"):
            from utils.exchange import usd_to_eur_rounded_up
            eur, rate, rate_date = usd_to_eur_rounded_up(
                total, order["date"], ecb_rates
            )
            pdf.cell(40, 7, "Total (EUR):", new_x="RIGHT")
            pdf.cell(
                0, 7,
                _safe(f"EUR {eur:.2f}  (rate {rate:.4f} on {rate_date})"),
                new_x="LMARGIN", new_y="NEXT",
            )
    pdf.ln(4)

    # Items table
    items = receipt_data.get("items", []) if receipt_data else []
    if items:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Items", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(110, 6, "Product", border=1)
        pdf.cell(25, 6, "Qty", border=1, align="C")
        pdf.cell(40, 6, "Price", border=1, align="R")
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for item in items:
            title = item.get("title", "")
            if len(title) > 65:
                title = title[:62] + "..."
            pdf.cell(110, 6, _safe(title), border=1)
            pdf.cell(
                25, 6, str(item.get("quantity", "1")),
                border=1, align="C",
            )
            pdf.cell(
                40, 6, _safe(item.get("price", "")),
                border=1, align="R",
            )
            pdf.ln()
    elif order.get("items"):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Items", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for idx, title in enumerate(order["items"], 1):
            text = _safe(title[:80])
            pdf.cell(
                0, 5, f"  {idx}. {text}",
                new_x="LMARGIN", new_y="NEXT",
            )
    pdf.ln(4)

    # Product images
    if product_images:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Product Images", new_x="LMARGIN", new_y="NEXT")
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        x_pos = x_start
        for img_path in product_images[:4]:
            if Path(str(img_path)).exists():
                try:
                    pdf.image(str(img_path), x=x_pos, y=y_start, w=35, h=35)
                    x_pos += 40
                except Exception:
                    pass
        if x_pos > x_start:
            pdf.set_y(y_start + 40)
        pdf.ln(2)

    # Octopart component identification (electronics only)
    if order.get("category") == "Electronics":
        _add_octopart_section(pdf, order, receipt_data)

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(
        0, 5,
        "Official receipt image on next page.",
        new_x="LMARGIN", new_y="NEXT",
    )


def _add_octopart_section(pdf, order, receipt_data):
    """Add Octopart component identification section to the PDF.

    Args:
        pdf: FPDF instance.
        order: Order dict.
        receipt_data: Optional dict with structured receipt data.
    """
    from utils.categorizer import extract_part_numbers, lookup_part
    from utils.config import octopart_search_url

    item_titles = []
    if receipt_data and receipt_data.get("items"):
        item_titles = [
            i.get("title", "") for i in receipt_data["items"]
            if i.get("title")
        ]
    elif order.get("items"):
        item_titles = order["items"]
    if not item_titles:
        return

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(
        0, 7, "Component Identification (Octopart)",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 8)
    for title in item_titles:
        parts = extract_part_numbers(title)
        if parts:
            for pn in parts:
                info = lookup_part(pn)
                if info:
                    text = (
                        f"{pn} - {info['manufacturer']}"
                        f" - {info['description']}"
                    )
                else:
                    text = f"{pn} - Search: {octopart_search_url(pn)}"
                pdf.cell(
                    0, 5, _safe(text),
                    new_x="LMARGIN", new_y="NEXT",
                )
        else:
            short = title[:55] if len(title) > 55 else title
            pdf.cell(
                0, 5, _safe(f"{short} -- no matching part"),
                new_x="LMARGIN", new_y="NEXT",
            )
    pdf.ln(2)


# -------------------------------------------------------------------
# Text-based PDF from receipt data
# -------------------------------------------------------------------

def generate_invoice_pdf(receipt_data, pdf_path):
    """Generate a PDF invoice with copyable text from receipt data.

    Args:
        receipt_data: Dict with structured receipt data.
        pdf_path: Path where to save the PDF.
    """
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(
        0, 12, "AliExpress Order Receipt",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )
    pdf.ln(8)

    # Order info
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Order Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    for label, value in [
        ("Order ID", receipt_data.get("order_id", "")),
        ("Order Time", receipt_data.get("order_time", "")),
    ]:
        if value:
            pdf.cell(40, 6, f"{label}:", new_x="RIGHT")
            pdf.cell(0, 6, _safe(value), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Items table
    items = receipt_data.get("items", [])
    if items:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Items", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(110, 6, "Product", border=1)
        pdf.cell(25, 6, "Qty", border=1, align="C")
        pdf.cell(40, 6, "Price", border=1, align="R")
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for item in items:
            title = item.get("title", "")
            if len(title) > 65:
                title = title[:62] + "..."
            pdf.cell(110, 6, _safe(title), border=1)
            pdf.cell(
                25, 6, str(item.get("quantity", "1")),
                border=1, align="C",
            )
            pdf.cell(40, 6, _safe(item.get("price", "")), border=1, align="R")
            pdf.ln()
        pdf.ln(4)

    # Financial summary
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Payment Details", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    for label, key in [("Subtotal", "subtotal"), ("Discount", "discount"),
                       ("Shipping", "shipping"), ("VAT", "vat")]:
        value = receipt_data.get(key, "")
        if value:
            pdf.cell(40, 6, f"{label}:", new_x="RIGHT")
            pdf.cell(0, 6, _safe(value), new_x="LMARGIN", new_y="NEXT")

    total = receipt_data.get("total", "")
    if total:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(40, 7, "Total:", new_x="RIGHT")
        pdf.cell(0, 7, _safe(total), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Shipping address
    address_lines = receipt_data.get("address_lines", [])
    if address_lines:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Shipping Address", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for line in address_lines:
            if line.strip():
                pdf.cell(
                    0, 6, _safe(line.strip()),
                    new_x="LMARGIN", new_y="NEXT",
                )
        pdf.ln(4)

    # Payment method
    payment = receipt_data.get("payment_method", "")
    if payment:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Payment Method", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for line in payment.split("\n"):
            if line.strip():
                pdf.cell(
                    0, 6, _safe(line.strip()),
                    new_x="LMARGIN", new_y="NEXT",
                )

    pdf.output(str(pdf_path))


# -------------------------------------------------------------------
# OCR helpers
# -------------------------------------------------------------------

def ocr_extract_text(image_path):
    """Extract text from an image using Tesseract OCR.

    Args:
        image_path: Path to the image file (PNG/JPG).

    Returns:
        Extracted text string, or empty string on failure.
    """
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        from PIL import Image

        with Image.open(str(image_path)) as img:
            text = pytesseract.image_to_string(img)
        return text
    except Exception as exc:
        print(f"    OCR extraction failed: {exc}")
        return ""


def ocr_extract_price(image_path):
    """Extract a USD price from a screenshot image via OCR.

    Useful for 2017-era orders where the tax-ui page has no data.

    Args:
        image_path: Path to the screenshot PNG.

    Returns:
        Float price in USD, or 0.0 if not found.
    """
    text = ocr_extract_text(image_path)
    if not text:
        return 0.0

    # Match patterns like "US $12.50", "$12.50", "USD 12.50"
    patterns = [
        r"US\s*\$\s*([\d,]+\.?\d*)",
        r"USD\s*([\d,]+\.?\d*)",
        r"\$\s*([\d,]+\.?\d*)",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            price_str = match.group(1).replace(",", "")
            try:
                return float(price_str)
            except ValueError:
                continue
    return 0.0


def verify_ocr_against_md(image_path, md_path):
    """Compare OCR text from an image against a Markdown invoice file.

    Extracts key fields (order ID, total price, item titles) from both
    the OCR text and the MD content and checks for matches.

    Args:
        image_path: Path to the screenshot image.
        md_path: Path to the companion .md file.

    Returns:
        Dict with match results: order_id_match, price_match,
        items_match_ratio, overall_match (bool).
    """
    ocr_text = ocr_extract_text(image_path)
    if not ocr_text:
        return {"order_id_match": False, "price_match": False,
                "items_match_ratio": 0.0, "overall_match": False}

    try:
        md_content = md_path.read_text(encoding="utf-8")
    except Exception:
        return {"order_id_match": False, "price_match": False,
                "items_match_ratio": 0.0, "overall_match": False}

    # Extract order ID from MD
    oid_match = re.search(r"Order\s+(\d{10,})", md_content)
    md_order_id = oid_match.group(1) if oid_match else ""

    # Check if order ID appears in OCR text
    order_id_match = bool(md_order_id and md_order_id in ocr_text)

    # Extract total price from MD
    price_md = re.search(r"\$\s*([\d,.]+)", md_content)
    md_price = price_md.group(1) if price_md else ""
    price_match = bool(md_price and md_price in ocr_text)

    # Extract item titles from MD (table rows)
    md_items = re.findall(r"\|\s*(.+?)\s*\|", md_content)
    md_items = [
        i.strip() for i in md_items
        if i.strip() and i.strip() != "Product"
        and not i.strip().startswith("---")
    ]

    # Check how many item words appear in OCR text
    ocr_lower = ocr_text.lower()
    matched = 0
    for item in md_items:
        words = item.lower().split()[:3]  # first 3 words
        if all(w in ocr_lower for w in words if len(w) > 2):
            matched += 1

    items_ratio = matched / max(len(md_items), 1)

    overall = order_id_match and price_match and items_ratio >= 0.5

    return {
        "order_id_match": order_id_match,
        "price_match": price_match,
        "items_match_ratio": items_ratio,
        "overall_match": overall,
    }


def pdf_to_image(pdf_path, dpi=72):
    """Render the first page of a PDF back to a PIL Image.

    Uses fpdf2's built-in rasterization when available, otherwise
    falls back to extracting embedded images from the PDF.

    Args:
        pdf_path: Path to the PDF file.
        dpi: Resolution for rendering (default 72).

    Returns:
        PIL Image object, or None on failure.
    """
    from PIL import Image

    # Extract the embedded full-page image from the PDF
    try:
        from fpdf import FPDF as _FPDF  # noqa: F811
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img
    except ImportError:
        pass

    # Fallback: extract the first image object from the PDF
    try:
        from PIL import PdfImagePlugin  # noqa: F401
        with Image.open(str(pdf_path)) as img:
            return img.copy()
    except Exception:
        pass

    return None


def compare_images_quarter_resolution(image_a, image_b):
    """Compare two images at quarter resolution using structural similarity.

    Both images are resized to quarter of image_a dimensions, converted
    to grayscale, and compared pixel-by-pixel for similarity.

    Args:
        image_a: PIL Image or path to image file.
        image_b: PIL Image or path to image file.

    Returns:
        Float similarity ratio between 0.0 and 1.0.
    """
    import numpy as np
    from PIL import Image

    if isinstance(image_a, (str, Path)):
        image_a = Image.open(str(image_a))
    if isinstance(image_b, (str, Path)):
        image_b = Image.open(str(image_b))

    # Quarter resolution of the first image
    quarter_w = max(image_a.width // 4, 1)
    quarter_h = max(image_a.height // 4, 1)

    a_resized = image_a.resize(
        (quarter_w, quarter_h), Image.LANCZOS
    ).convert("L")
    b_resized = image_b.resize(
        (quarter_w, quarter_h), Image.LANCZOS
    ).convert("L")

    arr_a = np.array(a_resized, dtype=np.float64)
    arr_b = np.array(b_resized, dtype=np.float64)

    # Normalized pixel-wise similarity: 1 - mean(abs_diff / 255)
    diff = np.abs(arr_a - arr_b) / 255.0
    similarity = 1.0 - np.mean(diff)

    return similarity
