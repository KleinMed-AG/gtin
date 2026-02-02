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
    """Create PDF matching Original.png exactly - CAREFUL MEASUREMENTS"""
    c = canvas.Canvas(output_file, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    # Load assets
    logo = load_image_safe("assets/image1.png")
    ce_mark = load_image_safe("assets/image2.png")
    md_symbol = load_image_safe("assets/image3.png")
    manufacturer_symbol = load_image_safe("assets/image6.png")
    manufacturer_symbol_empty = load_image_safe("assets/image8.png")
    ec_rep_symbol = load_image_safe("assets/image10.png")
    sn_symbol = load_image_safe("assets/image12.png")
    udi_symbol = load_image_safe("assets/image14.png")
    spec_symbols = load_image_safe("assets/Screenshot 2026-01-28 100951.png")

    # MARGINS - measured from Original
    left_margin = 0.15 * inch
    top_margin = 0.14 * inch
    right_margin = 0.18 * inch
    bottom_margin = 0.14 * inch

    for i in range(count):
        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        if i > 0:
            c.showPage()
            c.setPageSize((LABEL_WIDTH, LABEL_HEIGHT))

        # === LEFT COLUMN ===
        left_y = LABEL_HEIGHT - top_margin
        
        # Logo - KleinMed
        if logo:
            logo_w = 0.86 * inch
            logo_h = 0.25 * inch
            c.drawImage(logo, left_margin, left_y - logo_h, 
                       width=logo_w, height=logo_h,
                       preserveAspectRatio=True, mask="auto")
            left_y -= (logo_h + 0.16 * inch)
        
        # Product title block (4 lines, bold)
        c.setFont("Helvetica-Bold", 5)
        c.drawString(left_margin, left_y, product["name_de"])
        left_y -= 6
        c.drawString(left_margin, left_y, product["name_en"])
        left_y -= 6
        c.drawString(left_margin, left_y, product["name_fr"])
        left_y -= 6
        c.drawString(left_margin, left_y, product["name_it"])
        left_y -= 8
        
        # Description paragraph (4 lines, regular)
        c.setFont("Helvetica", 4)
        line_spacing = 5.5
        c.drawString(left_margin, left_y, product["description_de"][:80])
        left_y -= line_spacing
        c.drawString(left_margin, left_y, product["description_en"][:80])
        left_y -= line_spacing
        c.drawString(left_margin, left_y, product["description_fr"][:80])
        left_y -= line_spacing
        c.drawString(left_margin, left_y, product["description_it"][:80])
        left_y -= 14
        
        # Manufacturer block with icon
        icon_size = 0.24 * inch
        icon_text_gap = 0.04 * inch
        
        if manufacturer_symbol:
            c.drawImage(manufacturer_symbol, left_margin, left_y - 0.12 * inch,
                       width=icon_size, height=icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        text_x = left_margin + icon_size + icon_text_gap
        c.setFont("Helvetica", 4)
        c.drawString(text_x, left_y, product["manufacturer"]["name"])
        left_y -= 6.5
        
        c.setFont("Helvetica", 3.5)
        c.drawString(text_x, left_y, product["manufacturer"]["address_line1"])
        left_y -= 6
        c.drawString(text_x, left_y, product["manufacturer"]["address_line2"])
        left_y -= 8
        
        # EC REP block with icon
        if ec_rep_symbol:
            c.drawImage(ec_rep_symbol, left_margin, left_y - 0.12 * inch,
                       width=icon_size, height=icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        text_x = left_margin + icon_size + icon_text_gap
        c.setFont("Helvetica", 4)
        c.drawString(text_x, left_y, product["distributor"]["name"])
        left_y -= 6.5
        
        c.setFont("Helvetica", 3.5)
        c.drawString(text_x, left_y, product["distributor"]["address_line1"])
        left_y -= 6
        
        # Format address line 2 with comma
        address_line2 = product["distributor"]["address_line2"]
        if "Lübeck" in address_line2 and "," not in address_line2:
            parts = address_line2.split()
            if len(parts) >= 3:
                address_line2 = f"{parts[0]} {parts[1]}, {' '.join(parts[2:])}"
        
        c.drawString(text_x, left_y, address_line2)
        
        # === RIGHT COLUMN - TOP SYMBOLS ===
        right_y = LABEL_HEIGHT - top_margin
        
        # Calculate positions from RIGHT to LEFT
        symbol_row_y = right_y - 0.02 * inch
        
        # CE mark (rightmost)
        ce_size = 0.23 * inch
        ce_x = LABEL_WIDTH - right_margin - ce_size
        if ce_mark:
            c.drawImage(ce_mark, ce_x, symbol_row_y - ce_size,
                       width=ce_size, height=ce_size,
                       preserveAspectRatio=True, mask="auto")
        
        # MD symbol with border (next to CE)
        md_size = 0.23 * inch
        md_gap = 0.04 * inch
        md_x = ce_x - md_size - md_gap
        
        # Draw MD border
        c.setLineWidth(0.8)
        c.rect(md_x - 0.02 * inch, symbol_row_y - md_size - 0.02 * inch, 
               md_size + 0.04 * inch, md_size + 0.04 * inch)
        
        if md_symbol:
            c.drawImage(md_symbol, md_x, symbol_row_y - md_size,
                       width=md_size, height=md_size,
                       preserveAspectRatio=True, mask="auto")
        
        # Spec symbols (temperature etc.) - next to MD
        if spec_symbols:
            spec_w = 1.12 * inch
            spec_h = 0.16 * inch
            spec_x = md_x - spec_w - md_gap
            c.drawImage(spec_symbols, spec_x, symbol_row_y - md_size,
                       width=spec_w, height=spec_h,
                       preserveAspectRatio=True, mask="auto")
        
        # Move down for data section
        right_y -= 0.28 * inch
        
        # === RIGHT COLUMN - DATA SECTION ===
        # Define column for right side data
        right_data_x = LABEL_WIDTH - right_margin - 1.35 * inch
        
        # GTIN row
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(right_data_x, right_y, "GTIN")
        
        c.setFont("Helvetica", 5)
        c.drawString(right_data_x + 0.35 * inch, right_y, f"(01){product['gtin']}")
        right_y -= 10
        
        # LOT/Manufacturing date row with icon
        icon_small = 0.11 * inch
        if manufacturer_symbol_empty:
            c.drawImage(manufacturer_symbol_empty, 
                       right_data_x + 0.32 * inch, right_y - 0.06 * inch,
                       width=icon_small, height=icon_small,
                       preserveAspectRatio=True, mask="auto")
        
        c.setFont("Helvetica", 5)
        c.drawString(right_data_x + 0.46 * inch, right_y, f"(11){mfg_date}")
        right_y -= 10
        
        # SN row with box and icon
        sn_box_x = right_data_x - 0.03 * inch
        sn_box_y = right_y - 0.08 * inch
        sn_box_w = 0.28 * inch
        sn_box_h = 0.14 * inch
        
        # Draw SN border
        c.setLineWidth(1.2)
        c.rect(sn_box_x, sn_box_y, sn_box_w, sn_box_h)
        
        # SN label
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(right_data_x, right_y, "SN")
        
        # SN icon
        if sn_symbol:
            c.drawImage(sn_symbol, 
                       right_data_x + 0.32 * inch, right_y - 0.06 * inch,
                       width=icon_small, height=icon_small,
                       preserveAspectRatio=True, mask="auto")
        
        # SN value
        c.setFont("Helvetica", 5)
        c.drawString(right_data_x + 0.46 * inch, right_y, f"(21){serial}")
        
        # === QR CODE ===
        qr_size = 0.72 * inch
        qr_size_px = int(qr_size * 2.8)
        qr_img = generate_qr_code(udi_payload, target_px=qr_size_px)
        
        qr_x = LABEL_WIDTH - right_margin - qr_size + 0.08 * inch
        qr_y = bottom_margin
        
        c.drawImage(qr_img, qr_x, qr_y, 
                   width=qr_size, height=qr_size)
        
        # === UDI LABEL with box ===
        udi_box_x = right_data_x - 0.03 * inch
        udi_box_y = qr_y + (qr_size / 2) - 0.05 * inch
        udi_box_w = 0.34 * inch
        udi_box_h = 0.14 * inch
        
        # Draw UDI border
        c.setLineWidth(1.2)
        c.rect(udi_box_x, udi_box_y, udi_box_w, udi_box_h)
        
        # UDI text
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(right_data_x, udi_box_y + 0.04 * inch, "UDI")

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
