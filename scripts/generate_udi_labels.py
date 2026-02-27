#!/usr/bin/env python3
"""
UDI Label Generator – InDesign Template Overlay Strategy
=========================================================
Design lives in InDesign (assets/label_template.pdf).
This script overlays only the 4 variable data fields per label:
  - GTIN value
  - Manufacturing date (LOT)
  - Serial number (SN)
  - QR code

All static content (names, descriptions, manufacturer, EC Rep,
symbols, logo) is baked into the InDesign-exported template PDF.

SETUP:
  1. Design the label in InDesign, export as PDF/X-4
  2. Save exported file as assets/label_template.pdf
  3. Open it in Acrobat → View > Show/Hide > Cursor Coordinates
     Set units to Points, then measure the X,Y of each blank field
  4. Update the OVERLAY COORDINATES section below with your measurements
"""

import argparse
import csv
import os
from io import BytesIO
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter
import qrcode
import json

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)


# ===========================================================
# OVERLAY COORDINATES
# ===========================================================
# Measure these in Acrobat: View > Show/Hide > Cursor Coordinates
# Units: Points. Origin is BOTTOM-LEFT of page.
# Each tuple is (x, y) of the text baseline or image bottom-left.
#
# HOW TO MEASURE:
#   - Open assets/label_template.pdf in Adobe Acrobat
#   - Go to Edit > Preferences > Units > Points
#   - Hover over where text should start → read coordinates
#   - Note: Acrobat shows from top-left, so convert:
#       reportlab_y = PAGE_HEIGHT - acrobat_y

OVERLAY = {
    # (x, y) baseline for "(01)XXXXXXXXXXXXXXXXX" GTIN value text
    "gtin_value":     (480, 148),   # ← UPDATE WITH YOUR MEASUREMENTS

    # (x, y) baseline for "(11)YYMMDD" manufacturing date text
    "lot_value":      (480, 128),   # ← UPDATE

    # (x, y) baseline for "(21)NNNNNN" serial number text
    "sn_value":       (480, 108),   # ← UPDATE

    # (x, y, width, height) for QR code image bounding box (in points)
    "qr_box":         (630, 35, 150, 150),  # ← UPDATE (x, y, w, h)
}

# Font for overlay text — must match your InDesign design
# For exact match, register the same font InDesign uses (see FONT NOTE below)
OVERLAY_FONT       = "Helvetica"
OVERLAY_FONT_BOLD  = "Helvetica-Bold"
OVERLAY_FONT_SIZE  = 17   # Match your InDesign font size

# FONT NOTE:
# If your InDesign template uses a custom font (e.g. "Frutiger", "Myriad Pro"),
# register it here so the overlay text matches exactly:
#
#   from reportlab.pdfbase import pdfmetrics
#   from reportlab.pdfbase.ttfonts import TTFont
#   pdfmetrics.registerFont(TTFont("Frutiger", "assets/fonts/Frutiger.ttf"))
#   OVERLAY_FONT = "Frutiger"


# ===========================================================
# HELPERS (unchanged from original)
# ===========================================================

def validate_manufacturing_date(mfg_date):
    if len(mfg_date) != 6 or not mfg_date.isdigit():
        raise ValueError("Manufacturing date must be 6 digits (YYMMDD)")
    month = int(mfg_date[2:4])
    day   = int(mfg_date[4:6])
    if not (1 <= month <= 12):
        raise ValueError("Invalid month")
    if not (1 <= day <= 31):
        raise ValueError("Invalid day")
    return mfg_date


def generate_udi_string(gtin, mfg_date, serial):
    return f"(01){gtin}(11){mfg_date}(21){serial}"


def generate_qr_code(data, size_pts):
    """Generate QR code as an ImageReader at the given point size."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    # Render at 4× for sharpness then let ReportLab scale to exact print size
    target_px = int(size_pts * 4)
    img = qr.make_image(fill_color="black", back_color="white").convert("L")
    img = img.resize((target_px, target_px), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


# ===========================================================
# OVERLAY LAYER
# ===========================================================

def build_overlay_page(gtin, mfg_date, serial, udi_payload):
    """
    Creates a single transparent PDF page with only the variable data.
    This is merged on top of the InDesign template page.
    Returns a BytesIO containing a one-page PDF.
    """
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=landscape(A4))

    ox = OVERLAY
    c.setFont(OVERLAY_FONT, OVERLAY_FONT_SIZE)

    # GTIN value
    c.drawString(ox["gtin_value"][0], ox["gtin_value"][1],
                 f"(01){gtin}")

    # Manufacturing date (LOT)
    c.drawString(ox["lot_value"][0], ox["lot_value"][1],
                 f"(11){mfg_date}")

    # Serial number
    c.drawString(ox["sn_value"][0], ox["sn_value"][1],
                 f"(21){serial}")

    # QR code
    qr_x, qr_y, qr_w, qr_h = ox["qr_box"]
    qr_img = generate_qr_code(udi_payload, qr_w)
    c.drawImage(qr_img, qr_x, qr_y, width=qr_w, height=qr_h)

    c.save()
    packet.seek(0)
    return packet


# ===========================================================
# MAIN PDF CREATION
# ===========================================================

TEMPLATE_PATH = "assets/label_template.pdf"


def create_label_pdf(product, mfg_date, serial_start, count, output_file):
    """
    Generates `count` label pages by overlaying variable data
    onto the InDesign-exported template PDF.
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"InDesign template not found at '{TEMPLATE_PATH}'.\n"
            "Export your InDesign label as PDF/X-4 and save it there."
        )

    template_reader = PdfReader(TEMPLATE_PATH)
    template_page   = template_reader.pages[0]

    writer = PdfWriter()

    for i in range(count):
        serial      = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        # Build the variable data overlay for this serial number
        overlay_pdf    = build_overlay_page(product["gtin"], mfg_date, serial, udi_payload)
        overlay_reader = PdfReader(overlay_pdf)
        overlay_page   = overlay_reader.pages[0]

        # Clone the template page so we don't mutate it across iterations
        from copy import deepcopy
        page = deepcopy(template_page)

        # Merge overlay on top of template
        page.merge_page(overlay_page)
        writer.add_page(page)

    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    with open(output_file, "wb") as f:
        writer.write(f)

    print(f"✓ PDF created: {output_file}")


# ===========================================================
# CSV (unchanged from original)
# ===========================================================

def create_csv_file(product, mfg_date, serial_start, count, output_file):
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "AI - GTIN", "Artikelnummer/GTIN", "Name", "Grund-einheit", "SN/LOT",
            "Kurztext I", "Warengruppe", "AI - Herstelldatum", "Herstelldatum",
            "AI - SN", "Seriennummer", "UDI", "GTIN-Etikett",
            "Herstelldatum-Ettkett", "Seriennummer-Etikett", "QR", "QR-Code"
        ])
        for i in range(count):
            serial  = serial_start + i
            udi     = generate_udi_string(product["gtin"], mfg_date, serial)
            qr_url  = f"https://image-charts.com/chart?cht=qr&chs=250x250&chl={udi}"
            writer.writerow([
                "(01)", product["gtin"], product["name_de"],
                product["grundeinheit"], product["sn_lot_type"],
                product["kurztext"], product["warengruppe"],
                "(11)", mfg_date, "(21)", serial, udi,
                f"(01){product['gtin']}", f"(11){mfg_date}", f"(21){serial}",
                udi, qr_url
            ])
    print(f"✓ CSV created: {output_file}")


# ===========================================================
# COORDINATE CALIBRATION TOOL
# ===========================================================

def calibrate(output_file="output/calibration_overlay.pdf"):
    """
    Generates a calibration PDF to help you find the right overlay coordinates.
    It overlays a grid and labelled test values onto the template so you can
    visually confirm positions before committing to OVERLAY constants.

    Run with:
        python generate_udi_labels.py --calibrate
    """
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Template not found at {TEMPLATE_PATH}. Generating standalone calibration grid.")
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=landscape(A4))
    else:
        template_reader = PdfReader(TEMPLATE_PATH)
        template_page   = template_reader.pages[0]
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=landscape(A4))

    # Draw a light grid every 10mm
    c.setStrokeColorRGB(0.8, 0.8, 0.9)
    c.setLineWidth(0.25)
    for x in range(0, int(PAGE_WIDTH) + 1, int(10 * mm)):
        c.line(x, 0, x, PAGE_HEIGHT)
        if x % (20 * mm) == 0:
            c.setFont("Helvetica", 5)
            c.setFillColorRGB(0.5, 0.5, 0.8)
            c.drawString(x + 1, 2, f"{x:.0f}pt")
            c.setFillColorRGB(0, 0, 0)
    for y in range(0, int(PAGE_HEIGHT) + 1, int(10 * mm)):
        c.line(0, y, PAGE_WIDTH, y)
        if y % (20 * mm) == 0:
            c.setFont("Helvetica", 5)
            c.setFillColorRGB(0.5, 0.5, 0.8)
            c.drawString(2, y + 1, f"{y:.0f}pt")
            c.setFillColorRGB(0, 0, 0)

    # Draw test values at current OVERLAY positions
    c.setStrokeColorRGB(1, 0, 0)
    c.setFillColorRGB(1, 0, 0)
    c.setFont(OVERLAY_FONT, OVERLAY_FONT_SIZE)

    ox = OVERLAY
    for key, label in [
        ("gtin_value", "(01)1234567890123"),
        ("lot_value",  "(11)260101"),
        ("sn_value",   "(21)999999"),
    ]:
        x, y = ox[key]
        c.drawString(x, y, label)
        c.setLineWidth(0.5)
        c.line(x - 3, y, x + 3, y)          # crosshair
        c.line(x, y - 3, x, y + 3)
        c.setFont("Helvetica", 6)
        c.drawString(x + 4, y + 4, f"{key} ({x},{y})")
        c.setFont(OVERLAY_FONT, OVERLAY_FONT_SIZE)

    # Draw QR placeholder box
    qr_x, qr_y, qr_w, qr_h = ox["qr_box"]
    c.setFillColorRGB(0.9, 0.9, 1.0)
    c.rect(qr_x, qr_y, qr_w, qr_h, fill=1, stroke=1)
    c.setFillColorRGB(1, 0, 0)
    c.setFont("Helvetica", 8)
    c.drawString(qr_x + 4, qr_y + qr_h / 2, f"QR ({qr_x},{qr_y}) {qr_w}×{qr_h}pt")

    c.save()
    packet.seek(0)

    writer = PdfWriter()
    if os.path.exists(TEMPLATE_PATH):
        overlay_reader  = PdfReader(packet)
        from copy import deepcopy
        page = deepcopy(template_reader.pages[0])
        page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)
    else:
        reader = PdfReader(packet)
        writer.add_page(reader.pages[0])

    os.makedirs("output", exist_ok=True)
    with open(output_file, "wb") as f:
        writer.write(f)
    print(f"✓ Calibration PDF: {output_file}")
    print("  Open in Acrobat and check that red text aligns to your blank fields.")
    print("  Adjust OVERLAY coordinates in this file, then re-run until aligned.")


# ===========================================================
# ENTRY POINT
# ===========================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-json",  required=False)
    parser.add_argument("--mfg-date",      required=False)
    parser.add_argument("--serial-start",  type=int, required=False)
    parser.add_argument("--count",         type=int, required=False)
    parser.add_argument("--calibrate",     action="store_true",
                        help="Generate a calibration overlay to tune coordinates")
    args = parser.parse_args()

    if args.calibrate:
        calibrate()
        return

    if not all([args.product_json, args.mfg_date, args.serial_start is not None, args.count]):
        parser.error("--product-json, --mfg-date, --serial-start, and --count are required")

    validate_manufacturing_date(args.mfg_date)
    product = json.loads(args.product_json)

    os.makedirs("output", exist_ok=True)
    safe_name   = product["name_de"].replace(" ", "_")[:30]
    base_name   = f"UDI_Label_{safe_name}_{args.serial_start}-{args.serial_start + args.count - 1}"
    pdf_file    = f"output/{base_name}.pdf"
    csv_file    = f"output/{base_name}.csv"

    create_label_pdf(product, args.mfg_date, args.serial_start, args.count, pdf_file)
    create_csv_file( product, args.mfg_date, args.serial_start, args.count, csv_file)


if __name__ == "__main__":
    main()
