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
    """Create PDF matching original exactly"""
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

    # Layout parameters - ADJUSTED MARGINS
    left_margin = 0.15 * inch
    top_margin = 0.14 * inch - (20/72) * inch  # Reduced by ~20px
    right_margin = 0.18 * inch + (10/72) * inch  # Increased by ~10px
    bottom_margin = 0.14 * inch - (50/72) * inch  # Reduced by ~50px
    
    # Two-column grid
    usable_width = LABEL_WIDTH - left_margin - right_margin
    left_column_width = usable_width * 0.62
    column_gap = 0.10 * inch
    right_column_left = left_margin + left_column_width + column_gap

    for i in range(count):
        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        if i > 0:
            c.showPage()
            c.setPageSize((LABEL_WIDTH, LABEL_HEIGHT))

        # === LEFT COLUMN ===
        left_y = LABEL_HEIGHT - top_margin
        
        # Logo - ADJUSTED: reduced height by 20%, moved up 40px, moved left 25px
        if logo:
            logo_w = 0.86 * inch
            logo_h = 0.25 * inch * 0.80  # Reduced by 20%
            logo_x = left_margin - (25/72) * inch  # Moved left by 25px
            logo_y = left_y - logo_h + (40/72) * inch  # Moved up by 40px
            c.drawImage(logo, logo_x, logo_y, 
                       width=logo_w, height=logo_h,
                       preserveAspectRatio=True, mask="auto")
            left_y -= (logo_h + 0.16 * inch)
        
        # MULTILINGUAL TITLE BLOCK - ADJUSTED: moved 15px right, reduced spacing by 50%, reduced font by 1pt
        title_x = left_margin + (15/72) * inch  # Moved 15px right
        c.setFont("Helvetica-Bold", 4)  # Reduced from 5 (was 6, then 5, now 4)
        line_spacing_title = 3  # Reduced by 50% from 6
        
        c.drawString(title_x, left_y, product["name_de"])
        left_y -= line_spacing_title
        
        c.drawString(title_x, left_y, product["name_en"])
        left_y -= line_spacing_title
        c.drawString(title_x, left_y, product["name_fr"])
        left_y -= line_spacing_title
        c.drawString(title_x, left_y, product["name_it"])
        left_y -= 8
        
        # MULTILINGUAL DESCRIPTION BLOCK - ADJUSTED: moved up 12-15px, reduced line spacing by 4px
        left_y += (13/72) * inch  # Move up by ~13px
        c.setFont("Helvetica", 4)
        line_spacing = 1.5  # Reduced by ~4px from 5.5
        
        c.drawString(left_margin, left_y, product["description_de"][:80])
        left_y -= line_spacing
        c.drawString(left_margin, left_y, product["description_en"][:80])
        left_y -= line_spacing
        c.drawString(left_margin, left_y, product["description_fr"][:80])
        left_y -= line_spacing
        c.drawString(left_margin, left_y, product["description_it"][:80])
        left_y -= 14
        
        # MANUFACTURER + EC REP ADDRESSES - ADJUSTED: moved down 50px, icon size reduced 20%, icon moved 10px closer
        left_y -= (50/72) * inch  # Move down by 50px
        icon_size = 0.14 * inch * 0.80  # Reduced by 20%
        icon_text_gap = 0.04 * inch - (10/72) * inch  # 10px closer to text
        
        if manufacturer_symbol:
            c.drawImage(manufacturer_symbol, left_margin, left_y - 0.08 * inch,
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
        
        # EC REP block
        if ec_rep_symbol:
            c.drawImage(ec_rep_symbol, left_margin, left_y - 0.08 * inch,
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
        
        # === RIGHT COLUMN ===
        right_y = LABEL_HEIGHT - top_margin
        
        # Regulatory symbols - ADJUSTED: moved up 15px, shifted 25px left, reduced spacing by 12px, reduced size by 13%
        symbol_row_y = right_y - 0.02 * inch + (15/72) * inch  # Moved up by 15px
        symbol_size = 0.13 * inch * 0.87  # Reduced by 13%
        symbol_spacing = 0.04 * inch - (12/72) * inch  # Reduced spacing by 12px
        
        current_x = LABEL_WIDTH - right_margin - symbol_size - (25/72) * inch  # Shifted 25px left
        
        # CE mark - ADJUSTED: reduced size by 25%, moved 15px left
        if ce_mark:
            ce_size = symbol_size * 0.75  # Reduced by 25%
            ce_x = current_x - (15/72) * inch  # Moved 15px left
            c.drawImage(ce_mark, ce_x, symbol_row_y - ce_size,
                       width=ce_size, height=ce_size,
                       preserveAspectRatio=True, mask="auto")
            current_x -= (ce_size + symbol_spacing)
        
        # MD symbol - ADJUSTED: reduced size by 20%, moved 15px left, moved 15px down
        if md_symbol:
            md_size = symbol_size * 0.80  # Reduced by 20%
            md_x = current_x - (15/72) * inch  # Moved 15px left
            md_y = symbol_row_y - md_size - (15/72) * inch  # Moved 15px down
            c.drawImage(md_symbol, md_x, md_y,
                       width=md_size, height=md_size,
                       preserveAspectRatio=True, mask="auto")
            current_x -= (md_size + symbol_spacing)
        
        # Spec symbols
        if spec_symbols:
            spec_w = 1.12 * inch
            spec_h = 0.16 * inch
            spec_x = current_x - spec_w
            c.drawImage(spec_symbols, spec_x, symbol_row_y - symbol_size,
                       width=spec_w, height=spec_h,
                       preserveAspectRatio=True, mask="auto")
        
        right_y -= 0.28 * inch
        
        # GTIN/SN/UDI blocks - ADJUSTED: shifted 50px left, removed LOT, reduced spacing, smaller icons, moved icons up
        block_spacing = 10
        label_value_gap = 2  # Reduced by ~5-6px from original
        identifier_x = right_column_left - (50/72) * inch  # Shifted 50px left
        icon_size_data = 0.11 * inch * 0.83  # Reduced by 17%
        icon_x = identifier_x - 0.14 * inch
        
        # GTIN block
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(identifier_x, right_y, "GTIN")
        right_y -= label_value_gap
        
        if udi_symbol:
            icon_y = right_y - 0.06 * inch + (10/72) * inch  # Moved up by 10px
            c.drawImage(udi_symbol, icon_x, icon_y,
                       width=icon_size_data, height=icon_size_data,
                       preserveAspectRatio=True, mask="auto")
        
        c.setFont("Helvetica", 5)
        c.drawString(identifier_x, right_y, f"(01){product['gtin']}")
        right_y -= block_spacing
        
        # LOT block - REMOVED as per requirements
        
        # SN block
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(identifier_x, right_y, "SN")
        right_y -= label_value_gap
        
        if sn_symbol:
            icon_y = right_y - 0.06 * inch + (10/72) * inch  # Moved up by 10px
            c.drawImage(sn_symbol, icon_x, icon_y,
                       width=icon_size_data, height=icon_size_data,
                       preserveAspectRatio=True, mask="auto")
        
        c.setFont("Helvetica", 5)
        c.drawString(identifier_x, right_y, f"(21){serial}")
        
        # QR CODE - ADJUSTED: moved up by 120px initially, then additional 70-80px
        qr_size = 0.72 * inch
        qr_size_px = int(qr_size * 2.8)
        qr_img = generate_qr_code(udi_payload, target_px=qr_size_px)
        
        qr_x = LABEL_WIDTH - right_margin - qr_size + 0.08 * inch
        qr_y = bottom_margin + (195/72) * inch  # Moved up by ~195px total (120 + 75)
        
        c.drawImage(qr_img, qr_x, qr_y, 
                   width=qr_size, height=qr_size)
        
        # UDI label - ADJUSTED: moved up by 110px and 15px right (combined with 60px adjustment)
        udi_label_x = identifier_x + (15/72) * inch  # Moved 15px right
        udi_label_y = qr_y + (qr_size / 2) - 0.05 * inch + (170/72) * inch  # Moved up by ~170px total
        
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(udi_label_x, udi_label_y, "UDI")

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
