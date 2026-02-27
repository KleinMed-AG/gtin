#!/usr/bin/env python3
"""
UDI Label Generator – InDesign Template Overlay
================================================
Drop-in replacement for the original generate_udi_labels.py.
Same CLI interface, same output structure, better design quality.

HOW IT WORKS
  1. Python overlays ONLY the 4 variable fields onto the InDesign template:
       • GTIN value       – constant per product run
       • Mfg date (LOT)   – constant per batch
       • Serial number    – increments per label
       • QR code          – encodes all three above
  2. All static design (names, descriptions, symbols, logo,
     manufacturer/EC-Rep blocks) lives in the InDesign PDF template.

SETUP
  1. Design the label in InDesign at A4 Landscape (297 × 210 mm).
     Leave white empty rectangles at the 4 variable zones listed below.
  2. Export → PDF/X-4, save as:  assets/label_template.pdf
  3. Run calibration to verify alignment:
       python generate_udi_labels.py --calibrate
  4. Fine-tune OVERLAY coordinates until calibration PDF matches target.

COORDINATE SYSTEM
  ReportLab origin = BOTTOM-LEFT of page.
  A4 Landscape     = 841.89 × 595.28 pt  (297 × 210 mm)
  1 mm             = 2.8346 pt

VARIABLE ZONE REFERENCE (mm from bottom-left corner of page)
  ┌──────────────────────────────────────────────────────────────┐
  │                                           ←──── 297mm ──────│
  │  . . . . . . .  ALL STATIC  . . . . . . . . . . . . . . .  │
  │                                                              │
  │                         GTIN value  x=224.7mm  y=145.8mm   │
  │                                                              │
  │                         LOT  value  x=224.7mm  y=125.8mm   │
  │                                                              │
  │                         SN   value  x=224.7mm  y=109.3mm   │
  │                                                              │
  │          QR 95.6×95.6mm  bottom-left  x=188.3mm  y=6.2mm  │
  │ 210mm                                                        │
  └──────────────────────────────────────────────────────────────┘
"""

import argparse
import csv
import os
from copy import deepcopy
from io import BytesIO

from PIL import Image
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
import qrcode
import json

# ── Page constants ──────────────────────────────────────────────────────
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)   # 841.89 × 595.28 pt
mm_ = mm                                  # alias for readability

# ── Template path ───────────────────────────────────────────────────────
TEMPLATE_PATH = "assets/label_template.pdf"


# ===========================================================
# OVERLAY COORDINATES
# ===========================================================
# All values in POINTS.  Origin = BOTTOM-LEFT of page.
#
# Derived by back-computing the original generate_udi_labels.py grid:
#
#   V3 = PAGE_WIDTH × 0.60 – 4mm  = 493.80pt
#   V4 = V3 + 24mm                = 561.83pt
#   HEADER_BOTTOM = (PAGE_HEIGHT – 18mm) – 40mm = 430.87pt
#   right_y_start = HEADER_BOTTOM – 8mm          = 408.19pt
#   text_block_x  = V4 + 75pt                    = 636.83pt
#
#   GTIN  y = right_y_start + 5               = 413.19pt
#   LOT   y = right_y_start – (14mm+7) – 5    = 356.50pt
#   SN    y = right_y_start – 2×(14mm+7) – 5  = 309.81pt
#
#   qr_size = 85mm × 1.25 × 0.9  = 271.13pt (95.6mm)
#   qr_x    = (PAGE_WIDTH – 18mm) – qr_size + 14pt = 533.74pt
#   qr_y    = 18mm + 3mm – 42pt                    =  17.52pt
#
# ── Edit numbers here after running --calibrate ─────────────────────────
OVERLAY = {
    # (x, y) text baseline; bottom-left in points
    "gtin_value":  (636.8, 413.2),   # "(01){gtin}"      Helvetica 17pt
    "lot_value":   (636.8, 356.5),   # "(11){mfg_date}"  Helvetica 17pt
    "sn_value":    (636.8, 309.8),   # "(21){serial}"    Helvetica 17pt

    # (x, y, width, height) all in points
    "qr_box":      (533.7,  17.5,  271.1, 271.1),
}

OVERLAY_FONT      = "Helvetica"
OVERLAY_FONT_SIZE = 17


# ===========================================================
# VALIDATION & UDI HELPERS  (unchanged from original)
# ===========================================================

def validate_manufacturing_date(mfg_date: str) -> str:
    if len(mfg_date) != 6 or not mfg_date.isdigit():
        raise ValueError("Manufacturing date must be 6 digits (YYMMDD)")
    month = int(mfg_date[2:4])
    day   = int(mfg_date[4:6])
    if not (1 <= month <= 12):
        raise ValueError(f"Invalid month: {month}")
    if not (1 <= day <= 31):
        raise ValueError(f"Invalid day: {day}")
    return mfg_date


def generate_udi_string(gtin: str, mfg_date: str, serial: int) -> str:
    return f"(01){gtin}(11){mfg_date}(21){serial}"


def generate_qr_code(data: str, width_pts: float) -> ImageReader:
    """Generate a high-resolution QR code scaled to `width_pts` points."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    target_px = int(width_pts * 4)   # 4× for crisp print rendering
    img = qr.make_image(fill_color="black", back_color="white").convert("L")
    img = img.resize((target_px, target_px), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


# ===========================================================
# OVERLAY LAYER BUILDER
# ===========================================================

def _build_overlay(gtin: str, mfg_date: str,
                   serial: int, udi_payload: str) -> BytesIO:
    """
    Create a single transparent PDF page containing ONLY the variable data.
    Returns a BytesIO buffer holding a one-page PDF.
    """
    buf = BytesIO()
    c   = canvas.Canvas(buf, pagesize=landscape(A4))
    c.setFont(OVERLAY_FONT, OVERLAY_FONT_SIZE)

    ox = OVERLAY

    # Text fields
    c.drawString(ox["gtin_value"][0], ox["gtin_value"][1], f"(01){gtin}")
    c.drawString(ox["lot_value"][0],  ox["lot_value"][1],  f"(11){mfg_date}")
    c.drawString(ox["sn_value"][0],   ox["sn_value"][1],   f"(21){serial}")

    # QR code
    qr_x, qr_y, qr_w, qr_h = ox["qr_box"]
    qr_img = generate_qr_code(udi_payload, qr_w)
    c.drawImage(qr_img, qr_x, qr_y, width=qr_w, height=qr_h)

    c.save()
    buf.seek(0)
    return buf


# ===========================================================
# MAIN PDF CREATION
# ===========================================================

def create_label_pdf(product: dict, mfg_date: str,
                     serial_start: int, count: int,
                     output_file: str) -> None:
    """
    Overlay variable data onto the InDesign template PDF, one page per label.
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"\n  Template not found: '{TEMPLATE_PATH}'\n"
            "  → Export your InDesign label as PDF/X-4 and save it there.\n"
            "  → Or run:  python generate_udi_labels.py --calibrate\n"
            "    to produce a calibration grid without needing a template."
        )

    template_reader = PdfReader(TEMPLATE_PATH)
    base_page       = template_reader.pages[0]
    writer          = PdfWriter()

    for i in range(count):
        serial      = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        overlay_buf  = _build_overlay(product["gtin"], mfg_date,
                                      serial, udi_payload)
        overlay_page = PdfReader(overlay_buf).pages[0]

        page = deepcopy(base_page)
        page.merge_page(overlay_page)
        writer.add_page(page)

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    with open(output_file, "wb") as f:
        writer.write(f)

    s = "s" if count > 1 else ""
    print(f"✓ PDF created: {output_file}  ({count} label{s})")


# ===========================================================
# CSV EXPORT  (unchanged from original)
# ===========================================================

def create_csv_file(product: dict, mfg_date: str,
                    serial_start: int, count: int,
                    output_file: str) -> None:
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "AI - GTIN", "Artikelnummer/GTIN", "Name", "Grund-einheit",
            "SN/LOT", "Kurztext I", "Warengruppe", "AI - Herstelldatum",
            "Herstelldatum", "AI - SN", "Seriennummer", "UDI",
            "GTIN-Etikett", "Herstelldatum-Ettkett", "Seriennummer-Etikett",
            "QR", "QR-Code",
        ])
        for i in range(count):
            serial  = serial_start + i
            udi     = generate_udi_string(product["gtin"], mfg_date, serial)
            qr_url  = (f"https://image-charts.com/chart"
                       f"?cht=qr&chs=250x250&chl={udi}")
            writer.writerow([
                "(01)", product["gtin"], product["name_de"],
                product["grundeinheit"], product["sn_lot_type"],
                product["kurztext"], product["warengruppe"],
                "(11)", mfg_date, "(21)", serial, udi,
                f"(01){product['gtin']}", f"(11){mfg_date}",
                f"(21){serial}", udi, qr_url,
            ])
    print(f"✓ CSV created: {output_file}")


# ===========================================================
# CALIBRATION TOOL
# ===========================================================

def calibrate(output_file: str = "output/calibration_overlay.pdf") -> None:
    """
    Writes a PDF showing:
      • Blue measurement grid (every 10mm, labelled in pt and mm)
      • Red crosshairs + sample values at the OVERLAY coordinates
      • Shaded QR placeholder box with size annotation

    Merge this over your InDesign template to verify that the red markers
    land exactly in your blank data zones before running real labels.

    Usage:
        python generate_udi_labels.py --calibrate
        python generate_udi_labels.py --calibrate --output debug_v2.pdf
    """
    buf = BytesIO()
    c   = canvas.Canvas(buf, pagesize=landscape(A4))

    # ── Grid ────────────────────────────────────────────────
    step = int(10 * mm_)
    for x in range(0, int(PAGE_WIDTH) + step, step):
        shade = 0.75 if (x // step) % 2 == 0 else 0.88
        c.setStrokeColorRGB(0.55, 0.65, shade)
        c.setLineWidth(0.25)
        c.line(x, 0, x, PAGE_HEIGHT)
        if (x // step) % 2 == 0:
            c.setFont("Helvetica", 5)
            c.setFillColorRGB(0.3, 0.3, 0.85)
            c.drawString(x + 1, 3, f"{x:.0f}pt/{x/mm_:.0f}mm")
            c.setFillColorRGB(0, 0, 0)

    for y in range(0, int(PAGE_HEIGHT) + step, step):
        shade = 0.75 if (y // step) % 2 == 0 else 0.88
        c.setStrokeColorRGB(0.55, 0.65, shade)
        c.setLineWidth(0.25)
        c.line(0, y, PAGE_WIDTH, y)
        if (y // step) % 2 == 0:
            c.setFont("Helvetica", 5)
            c.setFillColorRGB(0.3, 0.3, 0.85)
            c.drawString(3, y + 1, f"{y:.0f}pt/{y/mm_:.0f}mm")
            c.setFillColorRGB(0, 0, 0)

    # ── Text field markers ──────────────────────────────────
    samples = [
        ("gtin_value", "(01)76499995659102", "GTIN value"),
        ("lot_value",  "(11)251104",          "LOT / mfg date"),
        ("sn_value",   "(21)8110007550",      "Serial number"),
    ]
    c.setFillColorRGB(0.85, 0, 0)
    c.setStrokeColorRGB(0.85, 0, 0)

    for key, sample, label in samples:
        x, y = OVERLAY[key]
        c.setFont(OVERLAY_FONT, OVERLAY_FONT_SIZE)
        c.drawString(x, y, sample)

        c.setLineWidth(0.6)
        c.line(x - 5, y, x + 5, y)   # crosshair
        c.line(x, y - 5, x, y + 5)

        c.setFont("Helvetica", 6.5)
        c.drawString(x + 6, y + 5,
                     f"{label}  ({x:.1f}pt, {y:.1f}pt) = "
                     f"({x/mm_:.1f}mm, {y/mm_:.1f}mm)")

    # ── QR placeholder ──────────────────────────────────────
    qr_x, qr_y, qr_w, qr_h = OVERLAY["qr_box"]
    c.setFillColorRGB(0.87, 0.87, 1.0)
    c.setStrokeColorRGB(0.85, 0, 0)
    c.setLineWidth(1.0)
    c.rect(qr_x, qr_y, qr_w, qr_h, fill=1, stroke=1)
    c.setFillColorRGB(0.85, 0, 0)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(qr_x + 5, qr_y + qr_h / 2 + 6,
                 f"QR CODE  {qr_w:.0f}×{qr_h:.0f}pt  "
                 f"({qr_w/mm_:.1f}×{qr_h/mm_:.1f}mm)")
    c.setFont("Helvetica", 7)
    c.drawString(qr_x + 5, qr_y + qr_h / 2 - 8,
                 f"origin  ({qr_x:.1f}pt, {qr_y:.1f}pt) = "
                 f"({qr_x/mm_:.1f}mm, {qr_y/mm_:.1f}mm)")

    # ── Header note ─────────────────────────────────────────
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(18, PAGE_HEIGHT - 14,
                 "CALIBRATION OVERLAY — red markers must align with blank "
                 "zones in InDesign template. Edit OVERLAY dict, re-run until aligned.")

    c.save()
    buf.seek(0)

    writer = PdfWriter()
    if os.path.exists(TEMPLATE_PATH):
        template_reader = PdfReader(TEMPLATE_PATH)
        page = deepcopy(template_reader.pages[0])
        page.merge_page(PdfReader(buf).pages[0])
        writer.add_page(page)
        print(f"  Merged calibration over: {TEMPLATE_PATH}")
    else:
        writer.add_page(PdfReader(buf).pages[0])
        print(f"  No template found at {TEMPLATE_PATH} — standalone grid generated.")

    os.makedirs("output", exist_ok=True)
    with open(output_file, "wb") as f:
        writer.write(f)

    print(f"✓ Calibration PDF: {output_file}")
    print()
    print("  WORKFLOW:")
    print("  1. Open calibration PDF in Acrobat/Preview")
    print("  2. Verify red text lands in your blank InDesign zones")
    print("  3. Adjust OVERLAY coordinates in this file (use mm annotations)")
    print("  4. Re-run --calibrate until aligned")
    print("  5. Then generate real labels with --product-json")


# ===========================================================
# ENTRY POINT
# ===========================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="UDI Label Generator – InDesign Template Overlay")
    parser.add_argument("--product-json",  help="Product data as JSON string")
    parser.add_argument("--mfg-date",      help="Manufacturing date YYMMDD")
    parser.add_argument("--serial-start",  type=int)
    parser.add_argument("--count",         type=int)
    parser.add_argument("--calibrate",     action="store_true",
                        help="Generate calibration overlay (no product data needed)")
    parser.add_argument("--output",        default=None,
                        help="Override calibration output path")
    args = parser.parse_args()

    if args.calibrate:
        calibrate(args.output or "output/calibration_overlay.pdf")
        return

    missing = [name for name, val in [
        ("--product-json", args.product_json),
        ("--mfg-date",     args.mfg_date),
        ("--serial-start", args.serial_start),
        ("--count",        args.count),
    ] if val is None]
    if missing:
        parser.error(f"Required when not using --calibrate: {', '.join(missing)}")

    validate_manufacturing_date(args.mfg_date)
    product = json.loads(args.product_json)

    os.makedirs("output", exist_ok=True)
    safe_name = product["name_de"].replace(" ", "_")[:30]
    end_sn    = args.serial_start + args.count - 1
    base      = f"output/UDI_Label_{safe_name}_{args.serial_start}-{end_sn}"

    create_label_pdf(product, args.mfg_date, args.serial_start,
                     args.count, f"{base}.pdf")
    create_csv_file( product, args.mfg_date, args.serial_start,
                     args.count, f"{base}.csv")


if __name__ == "__main__":
    main()
