#!/usr/bin/env python3
"""
UDI Label Generator for A4 Landscape
Grid-Based Master Layout – Precision Anchor System
Near-Perfect Structural Replica of Original Label
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
    month = int(mfg_date[2:4])
    day = int(mfg_date[4:6])
    if not (1 <= month <= 12):
        raise ValueError("Invalid month in manufacturing date")
    if not (1 <= day <= 31):
        raise ValueError("Invalid day in manufacturing date")
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
    img = img.resize((target_px, target_px), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def load_image_safe(path):
    if os.path.exists(path):
        return ImageReader(path)
    return None


# ==========================================================
# MASTER GRID LAYOUT SYSTEM
# ==========================================================

def create_label_pdf(product, mfg_date, serial_start, count, output_file):

    c = canvas.Canvas(output_file, pagesize=landscape(A4))

    # ----------- GRID CONSTRUCTION LINES -----------

    MARGIN_LEFT = 18 * mm
    MARGIN_RIGHT = 18 * mm
    MARGIN_TOP = 18 * mm
    MARGIN_BOTTOM = 18 * mm

    # Primary vertical grid
    LEFT_COLUMN_X = MARGIN_LEFT
    CENTER_DIVIDER_X = PAGE_WIDTH * 0.60
    RIGHT_EDGE_X = PAGE_WIDTH - MARGIN_RIGHT

    # Header band
    HEADER_TOP_Y = PAGE_HEIGHT - MARGIN_TOP
    HEADER_BOTTOM_Y = HEADER_TOP_Y - 40 * mm

    # QR zone
    QR_ZONE_BOTTOM = MARGIN_BOTTOM
    QR_ZONE_TOP = QR_ZONE_BOTTOM + 95 * mm

    # Right column data baseline
    RIGHT_DATA_START_Y = HEADER_BOTTOM_Y - 10 * mm

    # Vertical rhythm spacing
    TITLE_LINE_SPACING = 8.2 * mm
    BODY_LINE_SPACING = 6.2 * mm
    BLOCK_SPACING = 14 * mm

    # ----------- LOAD ASSETS -----------

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

        # ==========================================================
        # HEADER ROW
        # ==========================================================

        if logo:
            logo_w = 115 * mm
            logo_h = 32 * mm
            c.drawImage(
                logo,
                LEFT_COLUMN_X,
                HEADER_TOP_Y - logo_h,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto"
            )

        symbol_size = 20 * mm
        symbol_y = HEADER_TOP_Y - symbol_size

        if ce_mark:
            c.drawImage(
                ce_mark,
                RIGHT_EDGE_X - symbol_size,
                symbol_y,
                width=symbol_size,
                height=symbol_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        if md_symbol:
            c.drawImage(
                md_symbol,
                RIGHT_EDGE_X - symbol_size * 2 - 5 * mm,
                symbol_y,
                width=symbol_size,
                height=symbol_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        if spec_symbols:
            spec_w = 85 * mm
            spec_h = 20 * mm
            c.drawImage(
                spec_symbols,
                RIGHT_EDGE_X - spec_w - symbol_size * 2 - 10 * mm,
                symbol_y,
                width=spec_w,
                height=spec_h,
                preserveAspectRatio=True,
                mask="auto"
            )

        # ==========================================================
        # LEFT COLUMN TEXT BLOCK
        # ==========================================================

        y = HEADER_BOTTOM_Y - 5 * mm

        c.setFont("Helvetica-Bold", 23)
        c.drawString(LEFT_COLUMN_X, y, product["name_de"])
        y -= TITLE_LINE_SPACING
        c.drawString(LEFT_COLUMN_X, y, product["name_en"])
        y -= TITLE_LINE_SPACING
        c.drawString(LEFT_COLUMN_X, y, product["name_fr"])
        y -= TITLE_LINE_SPACING
        c.drawString(LEFT_COLUMN_X, y, product["name_it"])

        y -= BLOCK_SPACING

        c.setFont("Helvetica", 16)
        c.drawString(LEFT_COLUMN_X, y, product["description_de"][:100])
        y -= BODY_LINE_SPACING
        c.drawString(LEFT_COLUMN_X, y, product["description_en"][:100])
        y -= BODY_LINE_SPACING
        c.drawString(LEFT_COLUMN_X, y, product["description_fr"][:100])
        y -= BODY_LINE_SPACING
        c.drawString(LEFT_COLUMN_X, y, product["description_it"][:100])

        y -= BLOCK_SPACING

        # Manufacturer
        icon_size = 18 * mm
        text_x = LEFT_COLUMN_X + icon_size + 5 * mm

        if manufacturer_symbol:
            c.drawImage(
                manufacturer_symbol,
                LEFT_COLUMN_X,
                y - icon_size + 4,
                width=icon_size,
                height=icon_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.setFont("Helvetica", 15)
        c.drawString(text_x, y, product["manufacturer"]["name"])
        y -= BODY_LINE_SPACING
        c.drawString(text_x, y, product["manufacturer"]["address_line1"])
        y -= BODY_LINE_SPACING
        c.drawString(text_x, y, product["manufacturer"]["address_line2"])

        y -= BLOCK_SPACING

        # EC REP
        ec_icon_size = 30 * mm

        if ec_rep_symbol:
            c.drawImage(
                ec_rep_symbol,
                LEFT_COLUMN_X,
                y - ec_icon_size + 4,
                width=ec_icon_size,
                height=ec_icon_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        ec_text_x = LEFT_COLUMN_X + ec_icon_size + 5 * mm

        c.drawString(ec_text_x, y, product["distributor"]["name"])
        y -= BODY_LINE_SPACING
        c.drawString(ec_text_x, y, product["distributor"]["address_line1"])
        y -= BODY_LINE_SPACING
        c.drawString(ec_text_x, y, product["distributor"]["address_line2"])

        # ==========================================================
        # RIGHT COLUMN DATA
        # ==========================================================

        right_y = RIGHT_DATA_START_Y

        value_x = CENTER_DIVIDER_X + 20 * mm
        label_x = CENTER_DIVIDER_X

        spacing = 14 * mm

        c.setFont("Helvetica-Bold", 20)
        c.drawString(label_x, right_y, "GTIN")

        c.setFont("Helvetica", 17)
        c.drawString(value_x, right_y, f"(01){product['gtin']}")
        right_y -= spacing

        if manufacturer_symbol_empty:
            c.drawImage(
                manufacturer_symbol_empty,
                label_x,
                right_y - 8 * mm,
                width=16 * mm,
                height=16 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.drawString(value_x, right_y, f"(11){mfg_date}")
        right_y -= spacing

        if sn_symbol:
            c.drawImage(
                sn_symbol,
                label_x,
                right_y - 8 * mm,
                width=16 * mm,
                height=16 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.drawString(value_x, right_y, f"(21){serial}")

        # ==========================================================
        # QR CODE BLOCK
        # ==========================================================

        qr_size = 85 * mm
        qr_size_px = int(qr_size * 4)

        qr_img = generate_qr_code(udi_payload, qr_size_px)

        qr_x = RIGHT_EDGE_X - qr_size
        qr_y = QR_ZONE_BOTTOM

        c.drawImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

        if udi_symbol:
            udi_size = 26 * mm
            c.drawImage(
                udi_symbol,
                qr_x - udi_size - 8 * mm,
                qr_y + (qr_size - udi_size) / 2,
                width=udi_size,
                height=udi_size,
                preserveAspectRatio=True,
                mask="auto"
            )

    c.save()
    print(f"✓ PDF created: {output_file}")


# ==========================================================
# CSV EXPORT
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

    print(f"✓ CSV created: {output_file}")


# ==========================================================
# ENTRY POINT
# ==========================================================

def main():
    parser = argparse.ArgumentParser(description="Generate UDI labels")
    parser.add_argument("--product-json", required=True)
    parser.add_argument("--mfg-date", required=True)
    parser.add_argument("--serial-start", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)

    args = parser.parse_args()

    validate_manufacturing_date(args.mfg_date)
    product = json.loads(args.product_json)

    os.makedirs("output", exist_ok=True)

    safe_name = product["name_de"].replace(" ", "_")[:30]
    base_filename = f"UDI_Label_{safe_name}_{args.serial_start}-{args.serial_start + args.count - 1}"

    pdf_file = f"output/{base_filename}.pdf"
    csv_file = f"output/{base_filename}.csv"

    create_label_pdf(product, args.mfg_date, args.serial_start, args.count, pdf_file)
    create_csv_file(product, args.mfg_date, args.serial_start, args.count, csv_file)


if __name__ == "__main__":
    main()
