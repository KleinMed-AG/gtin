#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import os
import json
from io import BytesIO

from PIL import Image
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

import qrcode

# ============================================================
# PAGE / LABEL SETUP  (Exact size: 3 x 2 inches)
# ============================================================

LABEL_WIDTH = 3 * inch       # 216 pt
LABEL_HEIGHT = 2 * inch      # 144 pt

# Calibrated margins to match "Original.png"
LEFT_MARGIN   = 0.08 * inch  # ~5.8 pt
RIGHT_MARGIN  = 0.08 * inch
TOP_MARGIN    = 0.08 * inch
BOTTOM_MARGIN = 0.16 * inch  # slightly larger bottom margin

USABLE_WIDTH = LABEL_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

# Two-column layout tuned to match Original
LEFT_COL_W   = 1.78 * inch   # left column width (text + icons)
COL_GAP      = 0.10 * inch
RIGHT_COL_X  = LEFT_MARGIN + LEFT_COL_W + COL_GAP

# ------------------------------------------------------------
# FONTS (ReportLab core fonts: Helvetica)
# ------------------------------------------------------------
TITLE_FONT       = "Helvetica-Bold"
TITLE_SIZE_PT    = 6.0
TITLE_LEADING_PT = 5.0  # tight line spacing

PARA_FONT        = "Helvetica"
PARA_SIZE_PT     = 5.0
PARA_LEADING_PT  = 5.5

ADDR_FONT_MAIN   = "Helvetica"
ADDR_MAIN_SIZE   = 5.0
ADDR_FONT_SMALL  = "Helvetica"
ADDR_SMALL_SIZE  = 4.5
ADDR_LEADING_PT  = 6.0

RIGHT_LABEL_FONT = "Helvetica-Bold"
RIGHT_LABEL_SIZE = 6.0
RIGHT_VALUE_FONT = "Helvetica"
RIGHT_VALUE_SIZE = 5.5
RIGHT_GAP_LABEL_TO_VALUE = 4.0  # label above value

# ------------------------------------------------------------
# ICONS / LOGOS (all calibrated to Original)
# ------------------------------------------------------------
LOGO_W_IN   = 0.85     # ~0.85" wide
LOGO_H_IN   = 0.26     # proportional height (auto if preserveAspectRatio=True)
LOGO_W      = LOGO_W_IN * inch
LOGO_H      = LOGO_H_IN * inch
LOGO_TOP_GAP = 0.16 * inch  # gap from logo bottom to title block

# Top-right composite "spec symbols" (temperature, keep-dry, booklet)
SPEC_W      = 1.00 * inch
SPEC_H      = 0.16 * inch
SPEC_Y_SHIFT = 0.00 * inch  # subtle vertical micro-adjust (keep 0)

# MD + CE at the right of the spec row
MD_CE_SIZE  = 0.11 * inch     # slightly smaller than before
MD_CE_GAP   = 0.04 * inch     # spacing between MD and CE

# Manufacturer / EC REP icon + text block
ORG_ICON_SIZE = 0.12 * inch   # reduced to match Original
ICON_TEXT_GAP = 0.04 * inch

# Right-column identifiers
ID_ICON_SIZE  = 0.10 * inch
ID_ROW_SPACING = 10.0         # vertical spacing between GTIN row and SN row

# QR / UDI
QR_SIZE_IN   = 0.68
QR_SIZE      = QR_SIZE_IN * inch
UDI_LEFT_X   = RIGHT_COL_X    # aligned to right column text left
UDI_Y_OFFSET = -2.0           # small optical tweak relative to QR centerline

# ============================================================
# HELPERS
# ============================================================

def generate_udi_string(gtin, mfg_date, serial):
    """GS1-style concatenation (no FNC1 encoding; encoded as plain text in QR)."""
    return f"(01){gtin}(11){mfg_date}(21){serial}"

def generate_qr_code(data, target_px):
    """Generate crisp QR PNG with standard quiet zone."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("L")
    img = img.resize((target_px, target_px), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)

def load_image_safe(path):
    """Load image if exists, else None."""
    if os.path.exists(path):
        try:
            return ImageReader(path)
        except Exception as e:
            print(f"Warning: Could not load {path}: {e}")
    return None

def draw_wrapped_lines(c, text, x, y_top, max_width, font_name, font_size, leading):
    """
    Draw text wrapped to max_width. Returns the new y after drawing.
    Wrap is greedy by words using stringWidth for accurate breaking.
    """
    c.setFont(font_name, font_size)
    words = text.split()
    line = []
    y = y_top
    while words:
        line.append(words.pop(0))
        line_text = " ".join(line)
        w = stringWidth(line_text, font_name, font_size)
        if w > max_width and len(line) > 1:
            # commit previous line without the last word
            last = line.pop()
            c.drawString(x, y, " ".join(line))
            y -= leading
            line = [last]
    if line:
        c.drawString(x, y, " ".join(line))
        y -= leading
    return y

# ============================================================
# CANVAS DRAWING
# ============================================================

def create_label_pdf(product, mfg_date, serial_start, count, output_file):
    """Create PDF that reproduces Original layout."""
    c = canvas.Canvas(output_file, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    # Load assets (filenames kept from your script)
    logo = load_image_safe("assets/image1.png")                # KleinMed/BioRelax logo (use the KleinMed for Original)
    ce_mark = load_image_safe("assets/image2.png")
    md_symbol = load_image_safe("assets/image3.png")
    manufacturer_symbol = load_image_safe("assets/image6.png")
    ec_rep_symbol = load_image_safe("assets/image10.png")
    sn_symbol = load_image_safe("assets/image12.png")
    udi_symbol = load_image_safe("assets/image14.png")
    spec_symbols = load_image_safe("assets/Screenshot 2026-01-28 100951.png")

    for i in range(count):
        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        if i > 0:
            c.showPage()
            c.setPageSize((LABEL_WIDTH, LABEL_HEIGHT))

        # ---------------- LEFT COLUMN ----------------
        left_x = LEFT_MARGIN
        left_y = LABEL_HEIGHT - TOP_MARGIN

        # 1) Logo (top-left)
        if logo:
            c.drawImage(
                logo,
                left_x, left_y - LOGO_H,
                width=LOGO_W, height=LOGO_H,
                preserveAspectRatio=True, mask="auto"
            )
            left_y -= (LOGO_H + LOGO_TOP_GAP)

        # 2) 4-line Title block (semi-bold feel)
        c.setFont(TITLE_FONT, TITLE_SIZE_PT)
        c.drawString(left_x, left_y, product["name_de"])
        left_y -= TITLE_LEADING_PT
        c.drawString(left_x, left_y, product["name_en"])
        left_y -= TITLE_LEADING_PT
        c.drawString(left_x, left_y, product["name_fr"])
        left_y -= TITLE_LEADING_PT
        c.drawString(left_x, left_y, product["name_it"])
        # Tight gap to paragraph
        left_y -= (TITLE_LEADING_PT + 1.0)

        # 3) 4-line indication paragraph (wrapped)
        max_text_w = LEFT_COL_W  # wrap within left column
        c.setFont(PARA_FONT, PARA_SIZE_PT)
        left_y = draw_wrapped_lines(c, product["description_de"], left_x, left_y, max_text_w, PARA_FONT, PARA_SIZE_PT, PARA_LEADING_PT)
        left_y = draw_wrapped_lines(c, product["description_en"], left_x, left_y, max_text_w, PARA_FONT, PARA_SIZE_PT, PARA_LEADING_PT)
        left_y = draw_wrapped_lines(c, product["description_fr"], left_x, left_y, max_text_w, PARA_FONT, PARA_SIZE_PT, PARA_LEADING_PT)
        left_y = draw_wrapped_lines(c, product["description_it"], left_x, left_y, max_text_w, PARA_FONT, PARA_SIZE_PT, PARA_LEADING_PT)
        # Additional gap before organizations
        left_y -= 4.0

        # 4) Manufacturer block (icon + two lines)
        if manufacturer_symbol:
            c.drawImage(
                manufacturer_symbol,
                left_x, left_y - (ORG_ICON_SIZE * 0.75),
                width=ORG_ICON_SIZE, height=ORG_ICON_SIZE,
                preserveAspectRatio=True, mask="auto"
            )
        text_x = left_x + ORG_ICON_SIZE + ICON_TEXT_GAP
        c.setFont(ADDR_FONT_MAIN, ADDR_MAIN_SIZE)
        c.drawString(text_x, left_y, product["manufacturer"]["name"])
        left_y -= ADDR_LEADING_PT
        c.setFont(ADDR_FONT_SMALL, ADDR_SMALL_SIZE)
        c.drawString(text_x, left_y, product["manufacturer"]["address_line1"])
        left_y -= ADDR_LEADING_PT
        c.drawString(text_x, left_y, product["manufacturer"]["address_line2"])
        left_y -= (ADDR_LEADING_PT + 2.0)

        # 5) EC REP block (icon + two lines)
        if ec_rep_symbol:
            c.drawImage(
                ec_rep_symbol,
                left_x, left_y - (ORG_ICON_SIZE * 0.75),
                width=ORG_ICON_SIZE, height=ORG_ICON_SIZE,
                preserveAspectRatio=True, mask="auto"
            )
        text_x = left_x + ORG_ICON_SIZE + ICON_TEXT_GAP
        c.setFont(ADDR_FONT_MAIN, ADDR_MAIN_SIZE)
        c.drawString(text_x, left_y, product["distributor"]["name"])
        left_y -= ADDR_LEADING_PT
        c.setFont(ADDR_FONT_SMALL, ADDR_SMALL_SIZE)
        c.drawString(text_x, left_y, product["distributor"]["address_line1"])
        left_y -= ADDR_LEADING_PT
        # Keep address line 2 as-is; (your special Lübeck comma rule removed to avoid moving text)
        c.drawString(text_x, left_y, product["distributor"]["address_line2"])

        # ---------------- RIGHT COLUMN ----------------
        right_y = LABEL_HEIGHT - TOP_MARGIN

        # A) Top-right spec row + MD + CE (smaller, tighter, higher, left-shifted)
        # Start placement from the right edge inwards
        # Place CE at far right, MD to its left, then the composite spec to the left of MD.
        ce_x = LABEL_WIDTH - RIGHT_MARGIN - MD_CE_SIZE
        ce_y = right_y - MD_CE_SIZE  # top aligned
        if ce_mark:
            c.drawImage(ce_mark, ce_x, ce_y, width=MD_CE_SIZE, height=MD_CE_SIZE, preserveAspectRatio=True, mask="auto")

        md_x = ce_x - MD_CE_GAP - MD_CE_SIZE
        md_y = right_y - MD_CE_SIZE
        if md_symbol:
            c.drawImage(md_symbol, md_x, md_y, width=MD_CE_SIZE, height=MD_CE_SIZE, preserveAspectRatio=True, mask="auto")

        spec_x = md_x - MD_CE_GAP - SPEC_W
        spec_y = right_y - SPEC_H + SPEC_Y_SHIFT
        if spec_symbols:
            c.drawImage(spec_symbols, spec_x, spec_y, width=SPEC_W, height=SPEC_H, preserveAspectRatio=True, mask="auto")

        # Move down below symbols
        right_y = min(ce_y, md_y, spec_y) - 10.0

        # B) GTIN and SN blocks (no LOT in Original)
        id_x = RIGHT_COL_X
        id_icon_x = id_x - (ID_ICON_SIZE + 0.06 * inch)

        # --- GTIN ---
        c.setFont(RIGHT_LABEL_FONT, RIGHT_LABEL_SIZE)
        c.drawString(id_x, right_y, "GTIN")
        right_y -= RIGHT_GAP_LABEL_TO_VALUE

        if udi_symbol:
            c.drawImage(udi_symbol, id_icon_x, right_y - (ID_ICON_SIZE * 0.55),
                        width=ID_ICON_SIZE, height=ID_ICON_SIZE, preserveAspectRatio=True, mask="auto")

        c.setFont(RIGHT_VALUE_FONT, RIGHT_VALUE_SIZE)
        c.drawString(id_x, right_y, f"(01){product['gtin']}")
        right_y -= ID_ROW_SPACING

        # --- SN ---
        c.setFont(RIGHT_LABEL_FONT, RIGHT_LABEL_SIZE)
        c.drawString(id_x, right_y, "SN")
        right_y -= RIGHT_GAP_LABEL_TO_VALUE

        if sn_symbol:
            c.drawImage(sn_symbol, id_icon_x, right_y - (ID_ICON_SIZE * 0.55),
                        width=ID_ICON_SIZE, height=ID_ICON_SIZE, preserveAspectRatio=True, mask="auto")

        c.setFont(RIGHT_VALUE_FONT, RIGHT_VALUE_SIZE)
        c.drawString(id_x, right_y, f"(21){serial}")

        # C) QR code (mid-right) + UDI label aligned to its centerline
        # Position QR vertically centered in the label’s right half
        qr_target_px = int(QR_SIZE * 2.8)  # high DPI for crisp edges
        qr_img = generate_qr_code(udi_payload, target_px=qr_target_px)

        qr_x = LABEL_WIDTH - RIGHT_MARGIN - QR_SIZE
        qr_y = (LABEL_HEIGHT - QR_SIZE) / 2.0  # true vertical center
        c.drawImage(qr_img, qr_x, qr_y, width=QR_SIZE, height=QR_SIZE)

        # "UDI" label placed left of QR, aligned on its vertical centerline
        udi_label_y = qr_y + (QR_SIZE / 2.0) + UDI_Y_OFFSET
        c.setFont(RIGHT_LABEL_FONT, RIGHT_LABEL_SIZE)
        c.drawString(UDI_LEFT_X, udi_label_y, "UDI")

    c.save()
    print(f"✓ PDF created: {output_file}")
    print(f"✓ Generated {count} labels (Serial {serial_start}-{serial_start + count - 1})")


def create_csv_file(product, mfg_date, serial_start, count, output_file):
    """Create CSV file matching your spreadsheet structure."""
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "AI - GTIN", "Artikelnummer/GTIN", "Name", "Grund-einheit", "SN/LOT",
            "Kurztext I", "Warengruppe", "AI - Herstelldatum", "Herstelldatum",
            "AI - SN", "Seriennummer", "UDI", "GTIN-Etikett",
            "Herstelldatum-Ettkett", "Seriennummer-Etikett", "QR", "QR-Code"
        ])

        for i in range(count):
            serial = serial_start + i
            udi = generate_udi_string(product["gtin"], mfg_date, serial)
            # Keep your external QR URL reference as-is
            qr_url = f"https://image-charts.com/chart?cht=qr&chs=250x250&chl={udi}"

            writer.writerow([
                "(01)", product["gtin"], product["name_de"],
                product["grundeinheit"], product["sn_lot_type"],
                product["kurztext"], product["warengruppe"],
                "(11)", mfg_date, "(21)", serial, udi,
                f"(01){product['gtin']}", f"(11){mfg_date}",
                f"(21){serial}", udi, qr_url
            ])

    print(f"✓ CSV created: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate UDI labels")
    parser.add_argument("--product-json", required=True, help="Product data as JSON string")
    parser.add_argument("--mfg-date", required=True, help="Manufacturing date (YYMMDD)")
    parser.add_argument("--serial-start", type=int, required=True, help="Starting serial number")
    parser.add_argument("--count", type=int, required=True, help="Number of labels")
    args = parser.parse_args()

    product = json.loads(args.product_json)
    os.makedirs("output", exist_ok=True)

    safe_name = product["name_de"].replace(" ", "_")[:30]
    base_filename = f"UDI_Klebe-Etiketten_{safe_name}_SN{args.serial_start}-SN{args.serial_start + args.count - 1}"
    pdf_file = f"output/{base_filename}.pdf"
    csv_file = f"output/{base_filename}.csv"

    create_label_pdf(product, args.mfg_date, args.serial_start, args.count, pdf_file)
    create_csv_file(product, args.mfg_date, args.serial_start, args.count, csv_file)


if __name__ == "__main__":
    main()
