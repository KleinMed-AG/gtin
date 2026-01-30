#!/usr/bin/env python3
import argparse
import csv
import os
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
import json

# Label dimensions: 3" x 2"
LABEL_WIDTH = 3 * inch
LABEL_HEIGHT = 2 * inch


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
        try:
            return ImageReader(path)
        except Exception as e:
            print(f"Warning: Could not load {path}: {e}")
    return None


def draw_wrapped_text(c, text, x, y, max_width, font="Helvetica", size=5.5):
    c.setFont(font, size)
    words = text.split()
    lines = []
    current = []

    for w in words:
        test = " ".join(current + [w])
        if c.stringWidth(test, font, size) <= max_width:
            current.append(w)
        else:
            lines.append(" ".join(current))
            current = [w]

    if current:
        lines.append(" ".join(current))

    line_height = size + 2
    for line in lines:
        c.drawString(x, y, line)
        y -= line_height

    return y


def create_label_pdf(product, mfg_date, serial_start, count, output_file):
    c = canvas.Canvas(output_file, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    # Assets
    logo = load_image_safe("assets/image1.png")
    ce_mark = load_image_safe("assets/image2.png")
    md_symbol = load_image_safe("assets/image3.png")
    manufacturer_symbol = load_image_safe("assets/image6.png")
    ec_rep_symbol = load_image_safe("assets/image10.png")
    sn_symbol = load_image_safe("assets/image12.png")
    udi_symbol = load_image_safe("assets/image14.png")
    spec_symbols = load_image_safe("assets/Screenshot 2026-01-28 100951.png")

    # Margins
    left_margin = 0.15 * inch
    right_margin = 0.15 * inch
    top_margin = 0.14 * inch

    # Columns (62% / 38%)
    usable_width = LABEL_WIDTH - left_margin - right_margin
    left_column_width = usable_width * 0.62
    split_x = left_margin + left_column_width

    for i in range(count):
        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        if i > 0:
            c.showPage()
            c.setPageSize((LABEL_WIDTH, LABEL_HEIGHT))

        # ==========================================================
        # TOP ROW
        # ==========================================================
        y = LABEL_HEIGHT - top_margin

        # Logo (left)
        if logo:
            logo_w = 0.52 * inch
            logo_h = 0.16 * inch
            c.drawImage(
                logo,
                left_margin,
                y - logo_h,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )

        # ==========================================================
        # RIGHT COLUMN REGULATORY STACK (SINGLE CURSOR)
        # ==========================================================
        reg_y = y
        symbol_size = 0.12 * inch
        right_x = LABEL_WIDTH - right_margin - symbol_size

        # MD + CE
        if ce_mark:
            c.drawImage(
                ce_mark,
                right_x,
                reg_y - symbol_size,
                width=symbol_size,
                height=symbol_size,
                preserveAspectRatio=True,
                mask="auto",
            )

        if md_symbol:
            c.drawImage(
                md_symbol,
                right_x - symbol_size - 0.03 * inch,
                reg_y - symbol_size,
                width=symbol_size,
                height=symbol_size,
                preserveAspectRatio=True,
                mask="auto",
            )

        reg_y -= symbol_size + 0.06 * inch

        # Spec symbols (part of regulatory column)
        if spec_symbols:
            spec_w = 0.82 * inch
            spec_h = 0.13 * inch
            c.drawImage(
                spec_symbols,
                split_x + 0.05 * inch,
                reg_y - spec_h,
                width=spec_w,
                height=spec_h,
                preserveAspectRatio=True,
                mask="auto",
            )
            reg_y -= spec_h + 0.10 * inch

        # ==========================================================
        # MIDDLE SECTION
        # ==========================================================
        middle_top = reg_y

        # LEFT: Product names
        left_y = middle_top
        c.setFont("Helvetica-Bold", 6)
        c.drawString(left_margin, left_y, product["name_de"])
        left_y -= 6

        c.setFont("Helvetica", 5.5)
        c.drawString(left_margin, left_y, product["name_en"])
        left_y -= 6
        c.drawString(left_margin, left_y, product["name_fr"])
        left_y -= 6
        c.drawString(left_margin, left_y, product["name_it"])
        left_y -= 8

        # LEFT: Descriptions (NOT bold)
        left_y = draw_wrapped_text(c, product["description_de"], left_margin, left_y, left_column_width)
        left_y -= 3
        left_y = draw_wrapped_text(c, product["description_en"], left_margin, left_y, left_column_width)
        left_y -= 3
        left_y = draw_wrapped_text(c, product["description_fr"], left_margin, left_y, left_column_width)
        left_y -= 3
        left_y = draw_wrapped_text(c, product["description_it"], left_margin, left_y, left_column_width)

        # RIGHT: GTIN / LOT / SN
        right_y = middle_top
        symbol_x = split_x + 0.05 * inch
        text_x = symbol_x + 0.16 * inch

        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(text_x, right_y, "GTIN")
        right_y -= 9

        if udi_symbol:
            c.drawImage(
                udi_symbol,
                symbol_x,
                right_y - 0.10 * inch,
                width=0.12 * inch,
                height=0.12 * inch,
                preserveAspectRatio=True,
                mask="auto",
            )

        c.setFont("Helvetica", 7)
        c.drawString(text_x, right_y, f"(01){product['gtin']}")
        right_y -= 9

        if manufacturer_symbol:
            c.drawImage(
                manufacturer_symbol,
                symbol_x,
                right_y - 0.10 * inch,
                width=0.12 * inch,
                height=0.12 * inch,
                preserveAspectRatio=True,
                mask="auto",
            )

        c.drawString(text_x, right_y, f"(11){mfg_date}")
        right_y -= 9

        if sn_symbol:
            c.drawImage(
                sn_symbol,
                symbol_x,
                right_y - 0.10 * inch,
                width=0.12 * inch,
                height=0.12 * inch,
                preserveAspectRatio=True,
                mask="auto",
            )

        c.drawString(text_x, right_y, f"(21){serial}")

        # ==========================================================
        # BOTTOM SECTION (DERIVED FROM FLOW)
        # ==========================================================
        bottom_top = min(left_y, right_y) - 0.30 * inch

        # LEFT: Manufacturer + EC REP
        bl_y = bottom_top
        text_x = left_margin

        if manufacturer_symbol:
            sym = 0.11 * inch
            c.drawImage(
                manufacturer_symbol,
                left_margin,
                bl_y - sym + 2,
                width=sym,
                height=sym,
                preserveAspectRatio=True,
                mask="auto",
            )
            text_x = left_margin + sym + 0.04 * inch

        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(text_x, bl_y, product["manufacturer"]["name"])
        bl_y -= 6

        c.setFont("Helvetica", 5.5)
        c.drawString(text_x, bl_y, product["manufacturer"]["address_line1"])
        bl_y -= 6
        c.drawString(text_x, bl_y, product["manufacturer"]["address_line2"])
        bl_y -= 8

        text_x = left_margin
        if ec_rep_symbol:
            sym = 0.11 * inch
            c.drawImage(
                ec_rep_symbol,
                left_margin,
                bl_y - sym + 2,
                width=sym,
                height=sym,
                preserveAspectRatio=True,
                mask="auto",
            )
            text_x = left_margin + sym + 0.04 * inch

        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(text_x, bl_y, product["distributor"]["name"])
        bl_y -= 6

        c.setFont("Helvetica", 5.5)
        c.drawString(text_x, bl_y, product["distributor"]["address_line1"])
        bl_y -= 6
        c.drawString(text_x, bl_y, product["distributor"]["address_line2"])

        # RIGHT: QR code
        qr_size = 0.85 * inch
        qr_px = int(qr_size * 2.8)
        qr_img = generate_qr_code(udi_payload, qr_px)

        c.drawImage(
            qr_img,
            split_x + 0.08 * inch,
            bottom_top - qr_size,
            width=qr_size,
            height=qr_size,
        )

    c.save()
    print(f"✓ PDF created: {output_file}")
    print(f"✓ Generated {count} labels")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-json", required=True)
    parser.add_argument("--mfg-date", required=True)
    parser.add_argument("--serial-start", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    args = parser.parse_args()

    product = json.loads(args.product_json)
    os.makedirs("output", exist_ok=True)

    create_label_pdf(
        product,
        args.mfg_date,
        args.serial_start,
        args.count,
        "output/UDI_labels.pdf",
    )


if __name__ == "__main__":
    main()
