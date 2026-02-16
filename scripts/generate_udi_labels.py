#!/usr/bin/env python3
"""
UDI Label Generator for A4 Landscape
Refined Alignment Version – Position Corrections Only
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
# LAYOUT (POSITION REFINEMENT ONLY)
# ==========================================================

def create_label_pdf(product, mfg_date, serial_start, count, output_file):

    c = canvas.Canvas(output_file, pagesize=landscape(A4))

    # --- ORIGINAL MARGINS RESTORED ---
    LEFT_MARGIN = 18 * mm
    RIGHT_MARGIN = 18 * mm
    TOP_MARGIN = 18 * mm
    BOTTOM_MARGIN = 18 * mm

    # --- STRUCTURAL RAILS (Adjusted) ---
    V1 = LEFT_MARGIN - 2 * mm            # Left text rail shifted LEFT
    V3 = PAGE_WIDTH * 0.60 - 8 * mm      # Data label rail moved LEFT significantly
    V4 = V3 + 30 * mm                    # Data value rail moved RIGHT for proper spacing
    V6 = PAGE_WIDTH - RIGHT_MARGIN       # Right boundary rail

    HEADER_TOP = PAGE_HEIGHT - TOP_MARGIN
    HEADER_BOTTOM = HEADER_TOP - 42 * mm  # Slightly taller header

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
        # HEADER
        # ======================================================

        if logo:
            logo_w = 120 * mm
            logo_h = 35 * mm
            c.drawImage(
                logo,
                V1 - 3 * mm,
                HEADER_TOP - logo_h + 1 * mm,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto"
            )

        symbol_size = 21 * mm
        symbol_y = HEADER_TOP - symbol_size - 1 * mm

        if spec_symbols:
            spec_w = 88 * mm
            spec_h = 21 * mm
            c.drawImage(
                spec_symbols,
                V6 - spec_w - 55 * mm,
                symbol_y,
                width=spec_w,
                height=spec_h,
                preserveAspectRatio=True,
                mask="auto"
            )

        if md_symbol:
            c.drawImage(
                md_symbol,
                V6 - 40 * mm,
                symbol_y,
                width=symbol_size,
                height=symbol_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        if ce_mark:
            c.drawImage(
                ce_mark,
                V6 - 18 * mm,
                symbol_y - 1 * mm,
                width=symbol_size,
                height=symbol_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        # ======================================================
        # LEFT COLUMN
        # ======================================================

        y = HEADER_BOTTOM - 2 * mm

        TITLE_SPACING = 8.5 * mm
        BODY_SPACING = 6.5 * mm

        c.setFont("Helvetica-Bold", 23)
        c.drawString(V1, y, product["name_de"])
        y -= TITLE_SPACING
        c.drawString(V1, y, product["name_en"])
        y -= TITLE_SPACING
        c.drawString(V1, y, product["name_fr"])
        y -= TITLE_SPACING
        c.drawString(V1, y, product["name_it"])

        y -= 13 * mm  # tightened gap

        c.setFont("Helvetica", 16)
        c.drawString(V1, y, product["description_de"][:120])
        y -= BODY_SPACING
        c.drawString(V1, y, product["description_en"][:120])
        y -= BODY_SPACING
        c.drawString(V1, y, product["description_fr"][:120])
        y -= BODY_SPACING
        c.drawString(V1, y, product["description_it"][:120])

        y -= 15 * mm

        icon_size = 18 * mm
        text_x = V1 + icon_size + 9 * mm

        if manufacturer_symbol:
            c.drawImage(
                manufacturer_symbol,
                V1,
                y - icon_size + 4,
                width=icon_size,
                height=icon_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.setFont("Helvetica", 15)
        c.drawString(text_x, y, product["manufacturer"]["name"])
        y -= BODY_SPACING
        c.drawString(text_x, y, product["manufacturer"]["address_line1"])
        y -= BODY_SPACING
        c.drawString(text_x, y, product["manufacturer"]["address_line2"])

        y -= 15 * mm

        ec_icon_size = 32 * mm

        if ec_rep_symbol:
            c.drawImage(
                ec_rep_symbol,
                V1,
                y - ec_icon_size + 4,
                width=ec_icon_size,
                height=ec_icon_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        ec_text_x = V1 + ec_icon_size + 9 * mm

        c.drawString(ec_text_x, y, product["distributor"]["name"])
        y -= BODY_SPACING
        c.drawString(ec_text_x, y, product["distributor"]["address_line1"])
        y -= BODY_SPACING
        c.drawString(ec_text_x, y, product["distributor"]["address_line2"])

        # ======================================================
        # RIGHT COLUMN
        # ======================================================

        right_y = HEADER_BOTTOM - 6 * mm

        c.setFont("Helvetica-Bold", 20)
        c.drawString(V3, right_y, "GTIN")

        c.setFont("Helvetica", 18)
        c.drawString(V4, right_y, f"(01){product['gtin']}")

        right_y -= 16 * mm

        if manufacturer_symbol_empty:
            c.drawImage(
                manufacturer_symbol_empty,
                V3,
                right_y - 10 * mm,
                width=18 * mm,
                height=18 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.drawString(V4, right_y, f"(11){mfg_date}")

        right_y -= 16 * mm

        if sn_symbol:
            c.drawImage(
                sn_symbol,
                V3,
                right_y - 9 * mm,
                width=18 * mm,
                height=18 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.drawString(V4, right_y, f"(21){serial}")

        # ======================================================
        # QR + UDI
        # ======================================================

        qr_size = 92 * mm
        qr_size_px = int(qr_size * 4)

        qr_img = generate_qr_code(udi_payload, qr_size_px)

        qr_x = V6 - qr_size
        qr_y = BOTTOM_MARGIN + 6 * mm

        c.drawImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

        if udi_symbol:
            udi_size = 28 * mm
            c.drawImage(
                udi_symbol,
                qr_x - udi_size - 12 * mm,
                qr_y + (qr_size - udi_size) / 2 + 2 * mm,
                width=udi_size,
                height=udi_size,
                preserveAspectRatio=True,
                mask="auto"
            )

    c.save()
    print(f"✓ PDF created: {output_file}")


# ==========================================================
# CSV (UNCHANGED)
# ==========================================================

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
            serial = serial_start + i
            udi = generate_udi_string(product["gtin"], mfg_date, serial)
            qr_url = f"https://image-charts.com/chart?cht=qr&chs=250x250&chl={udi}"
            writer.writerow([
                "(01)", product["gtin"], product["name_de"],
                product["grundeinheit"], product["sn_lot_type"],
                product["kurztext"], product["warengruppe"],
                "(11)", mfg_date, "(21)", serial, udi,
                f"(01){product['gtin']}",
                f"(11){mfg_date}",
                f"(21){serial}",
                udi,
                qr_url
            ])


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

    pdf_file = "output/label.pdf"
    csv_file = "output/label.csv"

    create_label_pdf(product, args.mfg_date, args.serial_start, args.count, pdf_file)
    create_csv_file(product, args.mfg_date, args.serial_start, args.count, csv_file)


if __name__ == "__main__":
    main()
