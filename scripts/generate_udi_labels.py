#!/usr/bin/env python3
import argparse
import csv
import os
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import inch
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
import json

# Label dimensions: 3" x 2"
LABEL_WIDTH = 3 * inch
LABEL_HEIGHT = 2 * inch

# --------- Helpers ---------
def generate_udi_string(gtin, mfg_date, serial):
    """
    Payload encoded into the code image (QR placeholder here).
    If we move to GS1 DataMatrix later, we'll update the encoder but keep this function.
    """
    # Keep AIs in canonical order for payload; parentheses fine for QR tests.
    return f"(01){gtin}(11){mfg_date}(21){serial}"

def generate_qr_code(data, target_px):
    """
    Generate a crisp QR code with adequate quiet zone (border=4),
    and resize to target_px preserving sharpness.
    """
    qr = qrcode.QRCode(
        version=None,  # let it fit automatically
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,  # quiet zone for print
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("L")

    # Resize with high-quality resampling
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

# --------- Drawing primitives ---------
def draw_text_line(c, text, x, y, font="Helvetica", size=6, bold=False):
    if bold:
        c.setFont("Helvetica-Bold", size)
    else:
        c.setFont(font, size)
    c.drawString(x, y, text)

def draw_multiline_block(c, lines, x, y_start, line_height, font="Helvetica", size=6, bold=False):
    y = y_start
    if bold:
        c.setFont("Helvetica-Bold", size)
    else:
        c.setFont(font, size)
    for line in lines:
        c.drawString(x, y, line)
        y -= line_height
    return y

# --------- Layout ---------
def create_label_pdf(product, mfg_date, serial_start, count, output_file):
    c = canvas.Canvas(output_file, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    # Assets
    logo = load_image_safe("assets/image1.png")           # BioRelax logo (if applicable)
    ce_mark = load_image_safe("assets/image2.png")        # CE
    md_symbol = load_image_safe("assets/image3.png")      # MD
    manufacturer_symbol = load_image_safe("assets/image6.png")  # Manufacturer
    ec_rep_symbol = load_image_safe("assets/image10.png")       # EC REP
    sn_symbol = load_image_safe("assets/image12.png")     # SN
    udi_symbol = load_image_safe("assets/image14.png")    # UDI
    spec_symbols = load_image_safe("assets/Screenshot 2026-01-28 100951.png")  # 1,5cm / -20C° / +60C°

    # Margins
    left = 0.15 * inch
    right = 0.15 * inch
    top = 0.12 * inch
    bottom = 0.18 * inch

    # Canonical line heights
    lh_header = 7.5      # header multilingual
    lh_body = 7.0        # addresses & product names
    lh_gs1 = 8.0         # human-readable GS1
    lh_labels = 8.0      # GTIN label

    for i in range(count):
        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        if i > 0:
            c.showPage()
            c.setPageSize((LABEL_WIDTH, LABEL_HEIGHT))

        # ---- TOP STRIP: logo (left), CE+MD (right) ----
        y = LABEL_HEIGHT - top
        if logo:
            logo_w, logo_h = 0.70 * inch, 0.20 * inch
            c.drawImage(logo, left, y - logo_h, width=logo_w, height=logo_h,
                        preserveAspectRatio=True, mask="auto")
        # Right top symbols
        top_icon_y = LABEL_HEIGHT - top - 0.02 * inch
        icon = 0.15 * inch
        x_right = LABEL_WIDTH - right - icon
        if ce_mark:
            c.drawImage(ce_mark, x_right, top_icon_y, width=icon, height=icon, preserveAspectRatio=True, mask="auto")
        if md_symbol:
            c.drawImage(md_symbol, x_right - icon - 0.05 * inch, top_icon_y, width=icon, height=icon, preserveAspectRatio=True, mask="auto")

        y = y - 0.24 * inch  # space below top strip

        # ---- MULTILINGUAL HEADER (bold continuous block) ----
        header_lines = [
            product["description_de"],
            product["description_en"],
            product["description_fr"],
            product["description_it"],
        ]
        y = draw_multiline_block(c, header_lines, left, y, lh_header, size=6.5, bold=True)
        y -= 0.06 * inch

        # ---- SPEC SYMBOLS (1,5 cm / -20C° / +60C°) under header, NOT in GTIN line ----
        if spec_symbols:
            spec_w, spec_h = 1.00 * inch, 0.15 * inch
            c.drawImage(spec_symbols, left, y - spec_h + 1, width=spec_w, height=spec_h,
                        preserveAspectRatio=True, mask="auto")
            y -= (spec_h + 0.06 * inch)

        # ---- Manufacturer (KleinMed AG) ----
        # symbol + name line
        text_x = left
        if manufacturer_symbol:
            h = 0.12 * inch
            c.drawImage(manufacturer_symbol, left, y - (h - 2), width=h, height=h, preserveAspectRatio=True, mask="auto")
            text_x = left + h + 0.04 * inch
        draw_text_line(c, product["manufacturer"]["name"], text_x, y, size=7, bold=True)
        y -= lh_body
        draw_text_line(c, product["manufacturer"]["address_line1"], text_x, y, size=6)
        y -= lh_body
        draw_text_line(c, product["manufacturer"]["address_line2"], text_x, y, size=6)
        y -= lh_body

        # ---- Product family (4 languages, bold continuous) ----
        prod_lines = [
            product["name_de"],
            product["name_en"],
            product["name_fr"],
            product["name_it"],
        ]
        y = draw_multiline_block(c, prod_lines, left, y, lh_body, size=6, bold=True)
        y -= 0.10 * inch

        # ---- EC REP / Distributor (Hälsa Pharma GmbH) ----
        text_x = left
        if ec_rep_symbol:
            h = 0.12 * inch
            c.drawImage(ec_rep_symbol, left, y - (h - 2), width=h, height=h, preserveAspectRatio=True, mask="auto")
            text_x = left + h + 0.04 * inch
        draw_text_line(c, product["distributor"]["name"], text_x, y, size=6, bold=True)
        y -= lh_body
        draw_text_line(c, product["distributor"]["address_line1"], text_x, y, size=6)
        y -= lh_body
        draw_text_line(c, product["distributor"]["address_line2"], text_x, y, size=6)
        y -= (lh_body + 2)

        # ---- GS1 human-readable line (single line; order: 21, 01, 11) ----
        gs1_text = f"(21){serial}  (01){product['gtin']}  (11){mfg_date}"
        draw_text_line(c, gs1_text, left, y, size=9)
        y -= (lh_gs1 + 2)

        # ---- "GTIN" label on its own line ----
        draw_text_line(c, "GTIN", left, y, size=8, bold=True)
        y -= (lh_labels + 2)

        # ---- Code image (QR placeholder), centered horizontally and lower on page ----
        # Target a smaller code and keep bottom margin generous to match original
        qr_size_in = 0.95 * inch
        qr_size_px = int(qr_size_in * 2.8)  # good DPI for print
        qr_img = generate_qr_code(udi_payload, target_px=qr_size_px)

        # Center horizontally between margins
        qr_x = (LABEL_WIDTH - qr_size_in) / 2
        # Place low but above bottom margin
        qr_y = max(bottom, y - qr_size_in - 0.02 * inch)
        c.drawImage(qr_img, qr_x, qr_y, width=qr_size_in, height=qr_size_in)

    c.save()
    print(f"✓ PDF created: {output_file} (labels: {serial_start}..{serial_start+count-1})")

def create_csv_file(product, mfg_date, serial_start, count, output_file):
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "AI - GTIN","Artikelnummer/GTIN","Name","Grund-einheit","SN/LOT","Kurztext I","Warengruppe",
            "AI - Herstelldatum","Herstelldatum","AI - SN","Seriennummer","UDI",
            "GTIN-Etikett","Herstelldatum-Ettkett","Seriennummer-Etikett","QR","QR-Code"
        ])
        for i in range(count):
            serial = serial_start + i
            udi = generate_udi_string(product["gtin"], mfg_date, serial)
            qr_url = f"https://image-charts.com/chart?cht=qr&chs=250x250&chl={udi}"
            writer.writerow([
                "(01)", product["gtin"], product["name_de"], product["grundeinheit"], product["sn_lot_type"],
                product["kurztext"], product["warengruppe"], "(11)", mfg_date, "(21)", serial, udi,
                f"(01){product['gtin']}", f"(11){mfg_date}", f"(21){serial}", udi, qr_url
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
    safe = product["name_de"].replace(" ", "_")[:30]
    base = f"UDI_Klebe-Etiketten_{safe}_SN{args.serial_start}-SN{args.serial_start + args.count - 1}"
    pdf_file = f"output/{base}.pdf"
    csv_file = f"output/{base}.csv"

    create_label_pdf(product, args.mfg_date, args.serial_start, args.count, pdf_file)
    create_csv_file(product, args.mfg_date, args.serial_start, args.count, csv_file)

if __name__ == "__main__":
    main()
