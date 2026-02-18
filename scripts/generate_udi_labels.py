#!/usr/bin/env python3
"""
UDI Label Generator for A4 Landscape
Precision Grid System – Final Alignment Pass
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
        raise ValueError("Invalid month")
    if not (1 <= day <= 31):
        raise ValueError("Invalid day")
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
# MASTER LAYOUT
# ==========================================================

def create_label_pdf(product, mfg_date, serial_start, count, output_file):

    c = canvas.Canvas(output_file, pagesize=landscape(A4))

    # --- MASTER GRID ---
    MARGIN_LEFT = 18 * mm
    MARGIN_RIGHT = 18 * mm
    MARGIN_TOP = 18 * mm
    MARGIN_BOTTOM = 18 * mm

    # Structural vertical rails
    V1 = MARGIN_LEFT                     # Left text rail
    V3 = PAGE_WIDTH * 0.60 - 4 * mm      # Data label rail (moved LEFT 4mm)
    V4 = V3 + 24 * mm                    # Data value rail (moved RIGHT ~5mm net)
    V6 = PAGE_WIDTH - MARGIN_RIGHT       # Right page rail

    HEADER_TOP = PAGE_HEIGHT - MARGIN_TOP
    HEADER_BOTTOM = HEADER_TOP - 40 * mm

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

        # CORRECTION 1: Logo moved LEFT 30pt total (previous 25pt + 5pt)
        if logo:
            logo_w = 115 * mm
            logo_h = 32 * mm
            c.drawImage(
                logo,
                V1 - 3 * mm - 30,  # 30pt total left movement
                HEADER_TOP - logo_h,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto"
            )

        symbol_size = 20 * mm
        symbol_y = HEADER_TOP - symbol_size

        # Increase spec-to-MD gap by 3mm
        if spec_symbols:
            spec_w = 85 * mm
            spec_h = 20 * mm
            c.drawImage(
                spec_symbols,
                V6 - spec_w - symbol_size * 2 - 13 * mm,
                symbol_y,
                width=spec_w,
                height=spec_h,
                preserveAspectRatio=True,
                mask="auto"
            )

        if md_symbol:
            md_size = symbol_size * 1.25 * 1.25 * 0.95  # 29.6875mm (unchanged)
            c.drawImage(
                md_symbol,
                V6 - symbol_size * 2 - 5 * mm - 30,  # -20pt - 10pt = -30pt left total
                symbol_y - 5 - 3 - 7,  # -8pt - 7pt = -15pt down total
                width=md_size,
                height=md_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        if ce_mark:
            # CE lowered 1mm
            c.drawImage(
                ce_mark,
                V6 - symbol_size,
                symbol_y - 1 * mm,
                width=symbol_size,
                height=symbol_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        # ======================================================
        # LEFT COLUMN
        # ======================================================

        y = HEADER_BOTTOM - 3.5 * mm  # Title moved UP 1.5mm

        TITLE_SPACING = 8.2 * mm
        BODY_SPACING = 6.2 * mm

        c.setFont("Helvetica-Bold", 23)
        c.drawString(V1, y, product["name_de"])
        y -= TITLE_SPACING
        c.drawString(V1, y, product["name_en"])
        y -= TITLE_SPACING
        c.drawString(V1, y, product["name_fr"])
        y -= TITLE_SPACING
        c.drawString(V1, y, product["name_it"])

        # Reduce title/description gap by 2mm
        y -= 12 * mm

        c.setFont("Helvetica", 16)
        c.drawString(V1, y, product["description_de"][:100])
        y -= BODY_SPACING
        c.drawString(V1, y, product["description_en"][:100])
        y -= BODY_SPACING
        c.drawString(V1, y, product["description_fr"][:100])
        y -= BODY_SPACING
        c.drawString(V1, y, product["description_it"][:100])

        # Manufacturer block moved UP 2mm
        y -= 12 * mm

        icon_size = 18 * mm
        # CORRECTION 3: Manufacturer logo and text moved RIGHT 63pt total (previous 62pt + 1pt)
        manufacturer_x_offset = 63  # 63pt total right movement
        text_x = V1 + icon_size + 8 * mm + manufacturer_x_offset

        if manufacturer_symbol:
            c.drawImage(
                manufacturer_symbol,
                V1 + manufacturer_x_offset,  # 63pt right
                y - icon_size + 4,
                width=icon_size,
                height=icon_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.setFont("Helvetica", 15)
        # CORRECTION 2: KleinMed AG text moved 10pt down total (-3pt - 7pt)
        mfr_text_y_offset = -10  # 10pt down total
        c.drawString(text_x, y + mfr_text_y_offset, product["manufacturer"]["name"])
        y -= BODY_SPACING
        c.drawString(text_x, y + mfr_text_y_offset, product["manufacturer"]["address_line1"])
        y -= BODY_SPACING
        c.drawString(text_x, y + mfr_text_y_offset, product["manufacturer"]["address_line2"])

        # EC REP block moved UP 2mm
        y -= 12 * mm

        # CORRECTION 4: EC REP symbol moved UP 38pt total (previous 35pt + 3pt)
        # Size: 41.015625mm (unchanged)
        ec_icon_size = 28 * mm * 1.25 * 1.25 * 1.25 * 0.75  # 41.015625mm
        ec_y_offset = 38  # 38pt total up movement

        if ec_rep_symbol:
            c.drawImage(
                ec_rep_symbol,
                V1,
                y - ec_icon_size + 4 + ec_y_offset,  # 38pt up
                width=ec_icon_size,
                height=ec_icon_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        ec_text_x = V1 + ec_icon_size + 8 * mm
        
        # CORRECTION 5: EC REP text (Hälsa Pharma GmbH) moved 3pt DOWN
        ec_text_y_offset = -3  # 3pt down

        c.drawString(ec_text_x, y + ec_text_y_offset, product["distributor"]["name"])
        y -= BODY_SPACING
        c.drawString(ec_text_x, y + ec_text_y_offset, product["distributor"]["address_line1"])
        y -= BODY_SPACING
        c.drawString(ec_text_x, y + ec_text_y_offset, product["distributor"]["address_line2"])

        # ======================================================
        # RIGHT COLUMN
        # ======================================================

        right_y = HEADER_BOTTOM - 8 * mm

        # CORRECTIONS 3 & 4: GTIN/LOT/SN block
        # Icons/labels: 60pt + 15pt = 75pt total
        # Numeric values: 68pt + 10pt = 78pt total
        text_block_x_offset = 78  # 78pt total for numeric values
        label_icon_x_offset = 75  # 75pt total for icons and labels

        c.setFont("Helvetica-Bold", 20)
        c.drawString(V3 + label_icon_x_offset, right_y, "GTIN")

        c.setFont("Helvetica", 17)
        c.drawString(V4 + text_block_x_offset, right_y, f"(01){product['gtin']}")

        right_y -= 14 * mm

        # LOT icon - UP 11pt total, RIGHT 75pt total, SCALED 150%
        lot_icon_y_offset = 11  # 11pt total up movement
        lot_icon_size = 16 * mm * 1.5  # 24mm (150% scale: 16mm × 1.5)

        if manufacturer_symbol_empty:
            c.drawImage(
                manufacturer_symbol_empty,
                V3 + label_icon_x_offset,  # 75pt right
                right_y - 9.5 * mm + lot_icon_y_offset,  # 11pt up
                width=lot_icon_size,
                height=lot_icon_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.drawString(V4 + text_block_x_offset, right_y, f"(11){mfg_date}")

        right_y -= 14 * mm

        # SN icon - RIGHT 75pt total, SCALED 150%
        sn_icon_size = 16 * mm * 1.5  # 24mm (150% scale: 16mm × 1.5)
        
        if sn_symbol:
            c.drawImage(
                sn_symbol,
                V3 + label_icon_x_offset,  # 75pt right
                right_y - 7 * mm,
                width=sn_icon_size,
                height=sn_icon_size,
                preserveAspectRatio=True,
                mask="auto"
            )

        c.drawString(V4 + text_block_x_offset, right_y, f"(21){serial}")

        # ======================================================
        # QR + UDI
        # ======================================================

        qr_size = 85 * mm
        qr_size_px = int(qr_size * 4)

        qr_img = generate_qr_code(udi_payload, qr_size_px)

        qr_x = V6 - qr_size
        qr_y = MARGIN_BOTTOM + 3 * mm  # QR moved UP 3mm

        c.drawImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

        if udi_symbol:
            udi_size = 26 * mm
            c.drawImage(
                udi_symbol,
                qr_x - udi_size - 11 * mm,  # moved LEFT 3mm
                qr_y + (qr_size - udi_size) / 2 + 2 * mm,  # moved UP 2mm
                width=udi_size,
                height=udi_size,
                preserveAspectRatio=True,
                mask="auto"
            )

    c.save()
    print(f"✓ PDF created: {output_file}")


# ==========================================================
# CSV
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

    safe_name = product["name_de"].replace(" ", "_")[:30]
    base_filename = f"UDI_Label_{safe_name}_{args.serial_start}-{args.serial_start + args.count - 1}"

    pdf_file = f"output/{base_filename}.pdf"
    csv_file = f"output/{base_filename}.csv"

    create_label_pdf(product, args.mfg_date, args.serial_start, args.count, pdf_file)
    create_csv_file(product, args.mfg_date, args.serial_start, args.count, csv_file)


if __name__ == "__main__":
    main()
