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

def generate_udi_string(gtin, mfg_date, serial):
    """Generate UDI string in GS1 format"""
    return f"(01){gtin}(11){mfg_date}(21){serial}"

def generate_qr_code(data, target_px):
    """Generate QR code with proper quiet zone"""
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
    """Load image if exists, return None otherwise"""
    if os.path.exists(path):
        try:
            return ImageReader(path)
        except Exception as e:
            print(f"Warning: Could not load {path}: {e}")
    return None

def create_label_pdf(product, mfg_date, serial_start, count, output_file):
    """Create PDF with UDI labels matching original.pdf exactly"""
    c = canvas.Canvas(output_file, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    # Load assets
    logo = load_image_safe("assets/image1.png")
    ce_mark = load_image_safe("assets/image2.png")
    md_symbol = load_image_safe("assets/image3.png")
    manufacturer_symbol = load_image_safe("assets/image6.png")
    ec_rep_symbol = load_image_safe("assets/image10.png")
    sn_symbol = load_image_safe("assets/image12.png")
    udi_symbol = load_image_safe("assets/image14.png")
    spec_symbols = load_image_safe("assets/Screenshot 2026-01-28 100951.png")

    # Precise margins matching original
    left_margin = 0.15 * inch
    top_margin = 0.12 * inch
    right_margin = 0.15 * inch

    for i in range(count):
        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        if i > 0:
            c.showPage()
            c.setPageSize((LABEL_WIDTH, LABEL_HEIGHT))

        y = LABEL_HEIGHT - top_margin

        # === TOP: Logo (left) and CE + MD symbols (right) ===
        if logo:
            logo_w = 0.70 * inch
            logo_h = 0.20 * inch
            c.drawImage(logo, left_margin, y - logo_h, 
                       width=logo_w, height=logo_h,
                       preserveAspectRatio=True, mask="auto")

        # CE and MD symbols on top right
        symbol_size = 0.15 * inch
        top_right_y = LABEL_HEIGHT - top_margin - 0.05 * inch
        right_x = LABEL_WIDTH - right_margin - symbol_size
        
        if ce_mark:
            c.drawImage(ce_mark, right_x, top_right_y,
                       width=symbol_size, height=symbol_size,
                       preserveAspectRatio=True, mask="auto")
        
        if md_symbol:
            c.drawImage(md_symbol, right_x - symbol_size - 0.05 * inch, top_right_y,
                       width=symbol_size, height=symbol_size,
                       preserveAspectRatio=True, mask="auto")

        y -= 0.24 * inch

        # === MULTILINGUAL HEADER (4 lines, bold, tight spacing) ===
        c.setFont("Helvetica-Bold", 6.5)
        line_height = 7.5
        
        c.drawString(left_margin, y, product["description_de"])
        y -= line_height
        c.drawString(left_margin, y, product["description_en"])
        y -= line_height
        c.drawString(left_margin, y, product["description_fr"])
        y -= line_height
        c.drawString(left_margin, y, product["description_it"])
        y -= 12

        # === SPEC SYMBOLS (temp/height) immediately after header ===
        if spec_symbols:
            spec_w = 1.00 * inch
            spec_h = 0.15 * inch
            c.drawImage(spec_symbols, left_margin, y - spec_h,
                       width=spec_w, height=spec_h,
                       preserveAspectRatio=True, mask="auto")
            y -= (spec_h + 8)

        # === MANUFACTURER (KleinMed AG) ===
        text_x = left_margin
        if manufacturer_symbol:
            sym_h = 0.12 * inch
            c.drawImage(manufacturer_symbol, left_margin, y - sym_h + 2,
                       width=sym_h, height=sym_h,
                       preserveAspectRatio=True, mask="auto")
            text_x = left_margin + sym_h + 0.04 * inch

        c.setFont("Helvetica-Bold", 7)
        c.drawString(text_x, y, product["manufacturer"]["name"])
        y -= 9

        c.setFont("Helvetica", 6)
        c.drawString(text_x, y, product["manufacturer"]["address_line1"])
        y -= 8
        c.drawString(text_x, y, product["manufacturer"]["address_line2"])
        y -= 11

        # === PRODUCT NAMES (4 languages, bold) ===
        c.setFont("Helvetica-Bold", 6)
        c.drawString(left_margin, y, product["name_de"])
        y -= 8

        c.setFont("Helvetica", 6)
        c.drawString(left_margin, y, product["name_en"])
        y -= 8
        c.drawString(left_margin, y, product["name_fr"])
        y -= 8
        c.drawString(left_margin, y, product["name_it"])
        y -= 11

        # === EC REP / DISTRIBUTOR (Hälsa Pharma GmbH) ===
        text_x = left_margin
        if ec_rep_symbol:
            sym_h = 0.12 * inch
            c.drawImage(ec_rep_symbol, left_margin, y - sym_h + 2,
                       width=sym_h, height=sym_h,
                       preserveAspectRatio=True, mask="auto")
            text_x = left_margin + sym_h + 0.04 * inch

        c.setFont("Helvetica-Bold", 6)
        c.drawString(text_x, y, product["distributor"]["name"])
        y -= 8

        c.setFont("Helvetica", 6)
        c.drawString(text_x, y, product["distributor"]["address_line1"])
        y -= 8
        
        # CRITICAL FIX: Ensure comma and space in "23562 Lübeck, Germany"
        address_line2 = product["distributor"]["address_line2"]
        # Make sure there's a comma after Lübeck
        if "Lübeck" in address_line2 and "Lübeck," not in address_line2:
            address_line2 = address_line2.replace("Lübeck", "Lübeck,")
        c.drawString(text_x, y, address_line2)
        y -= 14

        # === CENTER COLUMN: GS1 Data Elements ===
        center_x = LABEL_WIDTH / 2 - 0.5 * inch
        gs1_y = LABEL_HEIGHT - top_margin - 0.95 * inch

        # Serial Number with SN symbol
        if sn_symbol:
            sym_size = 0.13 * inch
            c.drawImage(sn_symbol, center_x - 0.16 * inch, gs1_y - 0.08 * inch,
                       width=sym_size, height=sym_size,
                       preserveAspectRatio=True, mask="auto")

        c.setFont("Helvetica", 9)
        c.drawString(center_x, gs1_y, f"(21){serial}")

        # GTIN with UDI symbol
        gs1_y -= 13
        if udi_symbol:
            sym_size = 0.13 * inch
            c.drawImage(udi_symbol, center_x - 0.16 * inch, gs1_y - 0.08 * inch,
                       width=sym_size, height=sym_size,
                       preserveAspectRatio=True, mask="auto")

        c.drawString(center_x, gs1_y, f"(01){product['gtin']}")

        # Manufacturing date
        gs1_y -= 13
        c.drawString(center_x, gs1_y, f"(11){mfg_date}")

        # GTIN label
        gs1_y -= 17
        c.setFont("Helvetica-Bold", 8)
        c.drawString(center_x, gs1_y, "GTIN")

        # === QR CODE (right side, properly sized and positioned) ===
        qr_size_inches = 0.95 * inch
        qr_size_px = int(qr_size_inches * 2.8)
        qr_img = generate_qr_code(udi_payload, target_px=qr_size_px)

        # Position: right side, vertically centered
        qr_x = LABEL_WIDTH - qr_size_inches - 0.20 * inch
        qr_y = (LABEL_HEIGHT - qr_size_inches) / 2 + 0.10 * inch

        c.drawImage(qr_img, qr_x, qr_y, 
                   width=qr_size_inches, height=qr_size_inches)

    c.save()
    print(f"✓ PDF created: {output_file}")
    print(f"✓ Generated {count} labels (Serial {serial_start}-{serial_start + count - 1})")

def create_csv_file(product, mfg_date, serial_start, count, output_file):
    """Create CSV file matching spreadsheet structure"""
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
