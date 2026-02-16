#!/usr/bin/env python3
"""
UDI Label Generator – Structural Proportion Corrected
Rebuilt grid to match original artwork proportions
"""

import argparse
import csv
import os
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
import json

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)


# ==========================================================
# VALIDATION
# ==========================================================

def validate_manufacturing_date(mfg_date):
    if len(mfg_date) != 6 or not mfg_date.isdigit():
        raise ValueError("Manufacturing date must be 6 digits (YYMMDD)")
    return mfg_date


def generate_udi_string(gtin, mfg_date, serial):
    return f"(01){gtin}(11){mfg_date}(21){serial}"


def generate_qr_code(data, target_px):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("L")
    img = img.resize((target_px, target_px), Image.Resampling.NEAREST)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def load_image_safe(path):
    if os.path.exists(path):
        return ImageReader(path)
    return None


# ==========================================================
# MASTER LAYOUT – PROPORTION MATCHED
# ==========================================================

def create_label_pdf(product, mfg_date, serial_start, count, output_file):

    c = canvas.Canvas(output_file, pagesize=landscape(A4))

    # --- MARGINS REDUCED TO MATCH ORIGINAL SCALE ---
    LEFT_MARGIN = 14 * mm
    RIGHT_MARGIN = 14 * mm
    TOP_MARGIN = 14 * mm
    BOTTOM_MARGIN = 14 * mm

    # --- COLUMN PROPORTIONS (Measured From Original) ---
    LEFT_COLUMN_WIDTH = PAGE_WIDTH * 0.58
    RIGHT_COLUMN_START = PAGE_WIDTH * 0.60

    RIGHT_EDGE = PAGE_WIDTH - RIGHT_MARGIN
    LEFT_EDGE = LEFT_MARGIN

    HEADER_HEIGHT = 48 * mm
    HEADER_TOP = PAGE_HEIGHT - TOP_MARGIN
    HEADER_BOTTOM = HEADER_TOP - HEADER_HEIGHT

    # Load assets
    logo = load_image_safe("assets/2a82bf22-0bef-4cfb-830f-349f1fc793ef-1.png")
    ce_mark = load_image_safe("assets/image2.png")
    md_symbol = load_image_safe("assets/image3.png")
    manufacturer_symbol = load_image_safe("assets/image6.png")
    manufacturer_symbol_empty = load_image_safe("assets/image8.png")
    ec_rep_symbol = load_image_safe("assets/image10.png")
    sn_symbol = load_image_safe("assets/image12.png")
    udi_symbol = load_image_safe("assets/image14.png")
    spec_symbols = load_image_safe("assets/Screenshot 2026-01-28 100951.png")

    for i in range(count):

        if i > 0:
            c.showPage()

        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        # ======================================================
        # HEADER (LARGER LIKE ORIGINAL)
        # ======================================================

        if logo:
            logo_w = 135 * mm
            logo_h = 38 * mm
            c.drawImage(
                logo,
                LEFT_EDGE,
                HEADER_TOP - logo_h,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto"
            )

        symbol_size = 22 * mm
        symbol_y = HEADER_TOP - symbol_size

        if spec_symbols:
            spec_w = 92 * mm
            spec_h = 22 * mm
            c.drawImage(
                spec_symbols,
                RIGHT_EDGE - spec_w - 55 * mm,
                symbol_y,
                width=spec_w,
                height=spec_h,
                preserveAspectRatio=True,
                mask="auto"
            )

        if md_symbol:
            c.drawImage(
                md_symbol,
                RIGHT_EDGE - 45 * mm,
                symbol_y,
                width=symbol_size,
                height=symbol_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        if ce_mark:
            c.drawImage(
                ce_mark,
                RIGHT_EDGE - 20 * mm,
                symbol_y,
                width=symbol_size,
                height=symbol_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        # ======================================================
        # LEFT COLUMN – SCALED UP
        # ======================================================

        y = HEADER_BOTTOM - 4 * mm

        TITLE_SPACING = 9 * mm
        BODY_SPACING = 7 * mm

        c.setFont("Helvetica-Bold", 26)
        c.drawString(LEFT_EDGE, y, product["name_de"])
        y -= TITLE_SPACING
        c.drawString(LEFT_EDGE, y, product["name_en"])
        y -= TITLE_SPACING
        c.drawString(LEFT_EDGE, y, product["name_fr"])
        y -= TITLE_SPACING
        c.drawString(LEFT_EDGE, y, product["name_it"])

        y -= 16 * mm

        c.setFont("Helvetica", 18)
        c.drawString(LEFT_EDGE, y, product["description_de"][:120])
        y -= BODY_SPACING
        c.drawString(LEFT_EDGE, y, product["description_en"][:120])
        y -= BODY_SPACING
        c.drawString(LEFT_EDGE, y, product["description_fr"][:120])
        y -= BODY_SPACING
        c.drawString(LEFT_EDGE, y, product["description_it"][:120])

        y -= 18 * mm

        icon_size = 22 * mm
        text_x = LEFT_EDGE + icon_size + 10 * mm

        if manufacturer_symbol:
            c.drawImage(
                manufacturer_symbol,
                LEFT_EDGE,
                y - icon_size + 5,
                width=icon_size,
                height=icon_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.setFont("Helvetica", 17)
        c.drawString(text_x, y, product["manufacturer"]["name"])
        y -= BODY_SPACING
        c.drawString(text_x, y, product["manufacturer"]["address_line1"])
        y -= BODY_SPACING
        c.drawString(text_x, y, product["manufacturer"]["address_line2"])

        y -= 18 * mm

        ec_icon_size = 34 * mm

        if ec_rep_symbol:
            c.drawImage(
                ec_rep_symbol,
                LEFT_EDGE,
                y - ec_icon_size + 5,
                width=ec_icon_size,
                height=ec_icon_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        ec_text_x = LEFT_EDGE + ec_icon_size + 10 * mm

        c.drawString(ec_text_x, y, product["distributor"]["name"])
        y -= BODY_SPACING
        c.drawString(ec_text_x, y, product["distributor"]["address_line1"])
        y -= BODY_SPACING
        c.drawString(ec_text_x, y, product["distributor"]["address_line2"])

        # ======================================================
        # RIGHT COLUMN – REBALANCED
        # ======================================================

        right_y = HEADER_BOTTOM - 10 * mm

        LABEL_X = RIGHT_COLUMN_START
        VALUE_X = RIGHT_COLUMN_START + 28 * mm

        c.setFont("Helvetica-Bold", 22)
        c.drawString(LABEL_X, right_y, "GTIN")

        c.setFont("Helvetica", 20)
        c.drawString(VALUE_X, right_y, f"(01){product['gtin']}")

        right_y -= 18 * mm

        if manufacturer_symbol_empty:
            c.drawImage(
                manufacturer_symbol_empty,
                LABEL_X,
                right_y - 11 * mm,
                width=20 * mm,
                height=20 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.drawString(VALUE_X, right_y, f"(11){mfg_date}")

        right_y -= 18 * mm

        if sn_symbol:
            c.drawImage(
                sn_symbol,
                LABEL_X,
                right_y - 10 * mm,
                width=20 * mm,
                height=20 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.drawString(VALUE_X, right_y, f"(21){serial}")

        # ======================================================
        # QR – DOMINANT LIKE ORIGINAL
        # ======================================================

        qr_size = 105 * mm
        qr_size_px = int(qr_size * 4)

        qr_img = generate_qr_code(udi_payload, qr_size_px)

        qr_x = RIGHT_EDGE - qr_size
        qr_y = BOTTOM_MARGIN + 8 * mm

        c.drawImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

        if udi_symbol:
            udi_size = 32 * mm
            c.drawImage(
                udi_symbol,
                qr_x - udi_size - 14 * mm,
                qr_y + (qr_size - udi_size) / 2,
                width=udi_size,
                height=udi_size,
                preserveAspectRatio=True,
                mask="auto"
            )

    c.save()
    print(f"✓ PDF created: {output_file}")


# ==========================================================
# MAIN
# ==========================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-json", required=True)
    parser.add_argument("--mfg-date", required=True)
    parser.add_argument("--serial-start", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)

    args = parser.parse_args()

    validate_manufacturing_date(args.mfg_date)
    product = json.loads(args.product_json)

    os.makedirs("output", exist_ok=True)

    pdf_file = f"output/label.pdf"

    create_label_pdf(product, args.mfg_date, args.serial_start, args.count, pdf_file)


if __name__ == "__main__":
    main()
