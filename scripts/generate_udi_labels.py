#!/usr/bin/env python3
"""
UDI Label Generator for A4 Landscape
Based on analysis of original PDF converted to HTML
A4 Landscape: 297mm × 210mm (841.89pt × 595.28pt or 11.69" × 8.27")
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

# A4 landscape dimensions
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)

def validate_manufacturing_date(mfg_date):
    """Validate manufacturing date in YYMMDD format"""
    if len(mfg_date) != 6:
        raise ValueError(f"Manufacturing date must be 6 digits (YYMMDD), got: {mfg_date}")
    
    try:
        year = int(mfg_date[0:2])
        month = int(mfg_date[2:4])
        day = int(mfg_date[4:6])
    except ValueError:
        raise ValueError(f"Manufacturing date must contain only digits, got: {mfg_date}")
    
    if month < 1 or month > 12:
        raise ValueError(f"Month (MM) must be between 01 and 12, got: {month:02d}")
    
    if day < 1 or day > 31:
        raise ValueError(f"Day (TT) must be between 01 and 31, got: {day:02d}")
    
    return mfg_date

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
    """Create A4 landscape label PDF matching original design"""
    c = canvas.Canvas(output_file, pagesize=landscape(A4))

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

    # Layout parameters matching the original PNG
    left_margin = 15 * mm
    top_margin = 15 * mm
    
    # Right column starts much earlier (around 60% across page)
    right_col_x = 165 * mm

    for i in range(count):
        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        if i > 0:
            c.showPage()

        # Current Y position (starting from top)
        y_pos = PAGE_HEIGHT - top_margin

        # === LEFT COLUMN ===
        
        # Logo (larger, more prominent)
        if logo:
            logo_w = 140 * mm
            logo_h = 40 * mm
            c.drawImage(logo, left_margin, y_pos - logo_h,
                       width=logo_w, height=logo_h,
                       preserveAspectRatio=True, mask="auto")
            y_pos -= (logo_h + 8 * mm)

        # Product titles (4 languages) - BOLD and larger
        c.setFont("Helvetica-Bold", 18)
        line_height = 6.5 * mm
        c.drawString(left_margin, y_pos, product["name_de"])
        y_pos -= line_height
        c.drawString(left_margin, y_pos, product["name_en"])
        y_pos -= line_height
        c.drawString(left_margin, y_pos, product["name_fr"])
        y_pos -= line_height
        c.drawString(left_margin, y_pos, product["name_it"])
        y_pos -= 10 * mm

        # Description (pain relief text) - Regular weight, good size
        c.setFont("Helvetica", 13)
        desc_line_height = 5 * mm
        c.drawString(left_margin, y_pos, product["description_de"][:100])
        y_pos -= desc_line_height
        c.drawString(left_margin, y_pos, product["description_en"][:100])
        y_pos -= desc_line_height
        c.drawString(left_margin, y_pos, product["description_fr"][:100])
        y_pos -= desc_line_height
        c.drawString(left_margin, y_pos, product["description_it"][:100])
        y_pos -= 15 * mm

        # Manufacturer block with factory icon
        mfr_y = y_pos
        if manufacturer_symbol:
            icon_size = 12 * mm
            c.drawImage(manufacturer_symbol, left_margin, mfr_y - icon_size,
                       width=icon_size, height=icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        c.setFont("Helvetica", 13)
        text_x = left_margin + 15 * mm
        c.drawString(text_x, mfr_y, product["manufacturer"]["name"])
        mfr_y -= 5 * mm
        c.setFont("Helvetica", 13)
        c.drawString(text_x, mfr_y, product["manufacturer"]["address_line1"])
        mfr_y -= 5 * mm
        c.drawString(text_x, mfr_y, product["manufacturer"]["address_line2"])
        y_pos = mfr_y - 10 * mm

        # EC REP block with box icon
        ec_y = y_pos
        if ec_rep_symbol:
            icon_size = 12 * mm
            c.drawImage(ec_rep_symbol, left_margin, ec_y - icon_size,
                       width=icon_size, height=icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        c.setFont("Helvetica", 13)
        c.drawString(text_x, ec_y, product["distributor"]["name"])
        ec_y -= 5 * mm
        c.setFont("Helvetica", 13)
        c.drawString(text_x, ec_y, product["distributor"]["address_line1"])
        ec_y -= 5 * mm
        
        address_line2 = product["distributor"]["address_line2"]
        if "Lübeck" in address_line2 and "," not in address_line2:
            parts = address_line2.split()
            if len(parts) >= 3:
                address_line2 = f"{parts[0]} {parts[1]}, {' '.join(parts[2:])}"
        c.drawString(text_x, ec_y, address_line2)

        # === RIGHT COLUMN ===
        
        right_y = PAGE_HEIGHT - top_margin

        # Top symbols row (specs, MD, CE) - all same size
        symbol_y = right_y - 3 * mm
        symbol_size = 14 * mm
        
        # CE mark (rightmost)
        ce_x = PAGE_WIDTH - left_margin - symbol_size
        if ce_mark:
            c.drawImage(ce_mark, ce_x, symbol_y - symbol_size,
                       width=symbol_size, height=symbol_size,
                       preserveAspectRatio=True, mask="auto")
        
        # MD symbol
        md_x = ce_x - symbol_size - 5 * mm
        if md_symbol:
            c.drawImage(md_symbol, md_x, symbol_y - symbol_size,
                       width=symbol_size, height=symbol_size,
                       preserveAspectRatio=True, mask="auto")
        
        # Spec symbols (3-box strip) - wider
        if spec_symbols:
            spec_w = 55 * mm
            spec_h = 14 * mm
            spec_x = md_x - spec_w - 5 * mm
            c.drawImage(spec_symbols, spec_x, symbol_y - spec_h,
                       width=spec_w, height=spec_h,
                       preserveAspectRatio=True, mask="auto")
        
        right_y -= 30 * mm

        # GTIN/LOT/SN blocks - aligned right
        value_x = PAGE_WIDTH - left_margin - 1 * mm
        
        # GTIN - bold label
        c.setFont("Helvetica-Bold", 16)
        gtin_label = "GTIN"
        gtin_label_width = c.stringWidth(gtin_label, "Helvetica-Bold", 16)
        c.drawRightString(value_x - 50 * mm, right_y, gtin_label)
        
        c.setFont("Helvetica", 14)
        c.drawRightString(value_x, right_y, f"(01){product['gtin']}")
        right_y -= 12 * mm
        
        # LOT with factory icon
        icon_x = value_x - 85 * mm
        if manufacturer_symbol_empty:
            icon_size = 10 * mm
            c.drawImage(manufacturer_symbol_empty, icon_x, right_y - icon_size/2,
                       width=icon_size, height=icon_size,
                       preserveAspectRatio=True, mask="auto")
        c.setFont("Helvetica", 14)
        c.drawRightString(value_x, right_y, f"(11){mfg_date}")
        right_y -= 12 * mm
        
        # SN with box icon
        if sn_symbol:
            icon_size = 10 * mm
            c.drawImage(sn_symbol, icon_x, right_y - icon_size/2,
                       width=icon_size, height=icon_size,
                       preserveAspectRatio=True, mask="auto")
        c.setFont("Helvetica", 14)
        c.drawRightString(value_x, right_y, f"(21){serial}")

        # QR Code (bottom-right, large)
        qr_size = 70 * mm
        qr_size_px = int(qr_size * 4)
        qr_img = generate_qr_code(udi_payload, target_px=qr_size_px)
        
        qr_x = PAGE_WIDTH - left_margin - qr_size
        qr_y = 15 * mm
        c.drawImage(qr_img, qr_x, qr_y,
                   width=qr_size, height=qr_size)
        
        # UDI label (box with text) next to QR - positioned to left
        c.setFont("Helvetica-Bold", 12)
        udi_box_w = 18 * mm
        udi_box_h = 10 * mm
        udi_box_x = qr_x - udi_box_w - 8 * mm
        udi_box_y = qr_y + (qr_size - udi_box_h) / 2
        
        # Draw UDI box
        c.rect(udi_box_x, udi_box_y, udi_box_w, udi_box_h, stroke=1, fill=0)
        c.drawCentredString(udi_box_x + udi_box_w/2, udi_box_y + 2.5 * mm, "UDI")

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
    
    # Validate manufacturing date
    try:
        validate_manufacturing_date(args.mfg_date)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
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
