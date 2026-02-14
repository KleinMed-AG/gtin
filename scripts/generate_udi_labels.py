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
    """Create PDF matching original exactly"""
    c = canvas.Canvas(output_file, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    # Load assets
    logo = load_image_safe("assets/2a82bf22-0bef-4cfb-830f-349f1fc793ef-1.png")
    ce_mark = load_image_safe("assets/image2.png")
    md_symbol = load_image_safe("assets/image3.png")
    manufacturer_symbol = load_image_safe("assets/image6.png")
    manufacturer_symbol_empty = load_image_safe("assets/image8.png")  # FIX 4: Use image8 for LOT
    ec_rep_symbol = load_image_safe("assets/image10.png")
    sn_symbol = load_image_safe("assets/image12.png")
    udi_symbol = load_image_safe("assets/image14.png")  # FIX 1: Use next to QR
    spec_symbols = load_image_safe("assets/Screenshot 2026-01-28 100951.png")

    # Layout parameters
    left_margin = 0.15 * inch
    top_margin = 0.14 * inch
    right_margin = 0.18 * inch
    bottom_margin = 0.14 * inch
    
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
        
        # Logo - 58% larger (50% + 8%), shifted +6pt X, +4pt Y
        if logo:
            logo_w = 0.86 * inch * 1.58  # 58% larger
            logo_h = 0.25 * inch * 1.58  # 58% larger
            logo_x = left_margin + (6 / 72 * inch)  # Shift +6pt X
            logo_y_shift = 4 / 72 * inch  # Shift +4pt Y
            c.drawImage(logo, logo_x, left_y - logo_h + logo_y_shift, 
                       width=logo_w, height=logo_h,
                       preserveAspectRatio=True, mask="auto")
            left_y -= (logo_h + 0.16 * inch - logo_y_shift)
        
        # Product title block - Size +3%, Shift +8pt Y
        product_name_font_size = 5 * 1.03  # +3% size
        product_name_y_shift = 8 / 72 * inch  # Shift +8pt Y
        left_y += product_name_y_shift
        
        c.setFont("Helvetica-Bold", product_name_font_size)
        c.drawString(left_margin, left_y, product["name_de"])
        left_y -= 6
        c.drawString(left_margin, left_y, product["name_en"])
        left_y -= 6
        c.drawString(left_margin, left_y, product["name_fr"])
        left_y -= 6
        c.drawString(left_margin, left_y, product["name_it"])
        left_y -= 8
        
        # Indication paragraph - Size +2%, Shift +6pt Y
        description_font_size = 4 * 1.02  # +2% size
        description_y_shift = 6 / 72 * inch  # Shift +6pt Y
        left_y += description_y_shift
        
        c.setFont("Helvetica", description_font_size)
        line_spacing = 5.5
        c.drawString(left_margin, left_y, product["description_de"][:80])
        left_y -= line_spacing
        c.drawString(left_margin, left_y, product["description_en"][:80])
        left_y -= line_spacing
        c.drawString(left_margin, left_y, product["description_fr"][:80])
        left_y -= line_spacing
        c.drawString(left_margin, left_y, product["description_it"][:80])
        left_y -= 14
        
        # Manufacturer block - moved 15pt to the right, Size -2%, Shift -4pt X, +6pt Y
        icon_text_gap = 0.04 * inch
        left_margin_adjusted_mfr = left_margin + (15 / 72 * inch) - (4 / 72 * inch)  # Original +15pt, now -4pt more = +11pt
        manufacturer_y_shift = 6 / 72 * inch  # Shift +6pt Y
        
        # Calculate text block height (3 lines: 6.5 + 6 + 6 = 18.5pt spacing)
        manufacturer_text_height = 18.5
        manufacturer_icon_size = (manufacturer_text_height / 72 * inch) * 0.85 * 0.98  # 15% smaller, then -2%
        
        left_y += manufacturer_y_shift  # Apply Y shift
        text_x = left_margin_adjusted_mfr + manufacturer_icon_size + icon_text_gap
        manufacturer_start_y = left_y
        
        # All text same size: 4pt * 0.98 = -2%
        manufacturer_font_size = 4 * 0.98
        c.setFont("Helvetica", manufacturer_font_size)
        c.drawString(text_x, left_y, product["manufacturer"]["name"])
        left_y -= 6.5
        
        c.setFont("Helvetica", manufacturer_font_size)
        c.drawString(text_x, left_y, product["manufacturer"]["address_line1"])
        left_y -= 6
        c.drawString(text_x, left_y, product["manufacturer"]["address_line2"])
        
        # Draw manufacturer icon vertically centered with the entire text block, then move 5pt up
        # Center of text block is at start minus half the total height
        text_block_center_y = manufacturer_start_y - (manufacturer_text_height / 72 * inch / 2)
        icon_y = text_block_center_y - (manufacturer_icon_size / 2) + (5 / 72 * inch)  # Move 5pt up
        
        if manufacturer_symbol:
            c.drawImage(manufacturer_symbol, left_margin_adjusted_mfr, icon_y,
                       width=manufacturer_icon_size, height=manufacturer_icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        left_y -= (8 - manufacturer_y_shift)  # Adjust spacing accounting for Y shift
        
        # EC REP block - moved 9pt to the right, symbol 50% larger, Size -2% for text
        # Calculate text block height (3 lines: 6.5 + 6 spacing = 12.5pt)
        left_margin_adjusted_ec = left_margin + (9 / 72 * inch)  # Move 9pt to the right (2pt more from 7pt)
        ec_rep_text_height = 12.5
        ec_rep_icon_size = (ec_rep_text_height / 72 * inch) * 1.75  # 75% larger total (25% + 50%)
        
        text_x = left_margin_adjusted_ec + ec_rep_icon_size + icon_text_gap
        ec_rep_start_y = left_y
        
        # All text same size: 4pt * 0.98 = -2%
        ec_rep_font_size = 4 * 0.98
        c.setFont("Helvetica", ec_rep_font_size)
        c.drawString(text_x, left_y, product["distributor"]["name"])
        left_y -= 6.5
        
        c.setFont("Helvetica", ec_rep_font_size)
        c.drawString(text_x, left_y, product["distributor"]["address_line1"])
        left_y -= 6
        
        # Format address line 2 with comma
        address_line2 = product["distributor"]["address_line2"]
        if "Lübeck" in address_line2 and "," not in address_line2:
            parts = address_line2.split()
            if len(parts) >= 3:
                address_line2 = f"{parts[0]} {parts[1]}, {' '.join(parts[2:])}"
        
        c.drawString(text_x, left_y, address_line2)
        
        # Draw EC REP icon vertically centered with the entire text block, then move 1pt up
        # Center of text block is at start minus half the total height
        text_block_center_y = ec_rep_start_y - (ec_rep_text_height / 72 * inch / 2)
        icon_y = text_block_center_y - (ec_rep_icon_size / 2) + (1 / 72 * inch)  # Move 1pt up
        
        if ec_rep_symbol:
            c.drawImage(ec_rep_symbol, left_margin_adjusted_ec, icon_y,
                       width=ec_rep_icon_size, height=ec_rep_icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        # Store EC REP text end position for QR alignment
        ec_rep_text_end_y = left_y
        
        # === RIGHT COLUMN ===
        right_y = LABEL_HEIGHT - top_margin
        
        # Regulatory symbols - MD and CE: Size 0% (keep current 25%), Shift -6pt Y
        symbol_row_y = right_y - 0.02 * inch - (6 / 72 * inch)  # Shift -6pt Y
        symbol_size = 0.13 * inch * 1.25  # 25% larger for CE and MD (no additional change)
        symbol_spacing = 0.04 * inch
        
        current_x = LABEL_WIDTH - right_margin - symbol_size
        ce_mark_right_edge = current_x + symbol_size  # Store CE mark right edge for QR alignment
        
        if ce_mark:
            c.drawImage(ce_mark, current_x, symbol_row_y - symbol_size,
                       width=symbol_size, height=symbol_size,
                       preserveAspectRatio=True, mask="auto")
            current_x -= (symbol_size + symbol_spacing)
        
        if md_symbol:
            c.drawImage(md_symbol, current_x, symbol_row_y - symbol_size,
                       width=symbol_size, height=symbol_size,
                       preserveAspectRatio=True, mask="auto")
            current_x -= (symbol_size + symbol_spacing)
        
        # Spec symbols - 45% larger and moved 15pt to the right
        if spec_symbols:
            spec_w = 1.12 * inch * 1.45  # 45% larger
            spec_h = 0.16 * inch * 1.45  # 45% larger
            spec_x = current_x - spec_w + (15 / 72 * inch)  # Move 15pt to the right
            c.drawImage(spec_symbols, spec_x, symbol_row_y - 0.13 * inch * 1.25,  # Adjust for larger symbol size
                       width=spec_w, height=spec_h,
                       preserveAspectRatio=True, mask="auto")
        
        right_y -= 0.28 * inch
        
        # Move entire GTIN/LOT/SN block 10pt down (was 3pt, now 7pt more)
        right_y -= (10 / 72 * inch)
        
        # GTIN/LOT/SN blocks - moved 2pt to the right
        block_spacing = 11  # Increased from 10 to 11 (1pt more spacing)
        identifier_x = right_column_left + (2 / 72 * inch) + (4 / 72 * inch)  # Original +2pt, now +4pt more = +6pt X for GTIN
        udi_icon_size = 0.22 * inch * 0.90  # UDI icon size - 10% smaller
        icon_size_small = udi_icon_size  # Make LOT and SN same size as UDI
        icon_number_gap = 0.05 * inch + (1 / 72 * inch)  # Add 1pt more spacing
        
        # Calculate the maximum width needed for labels/icons to align numbers
        gtin_font_size = 6.5 * 0.85 * 1.10  # 15% smaller, then +10% = 6.5 * 0.935
        c.setFont("Helvetica-Bold", gtin_font_size)
        gtin_label_width = c.stringWidth("GTIN", "Helvetica-Bold", gtin_font_size)
        
        # The maximum width is either the GTIN label or the icon size
        max_label_width = max(gtin_label_width, icon_size_small)
        number_start_x = identifier_x + max_label_width + icon_number_gap
        
        # FIX 2: GTIN block - "GTIN" text LEFT of number, Size +10%, Shift +4pt X, -2pt Y
        gtin_y_shift = -2 / 72 * inch  # Shift -2pt Y
        c.setFont("Helvetica-Bold", gtin_font_size)
        c.drawString(identifier_x, right_y + gtin_y_shift, "GTIN")
        
        number_font_size = 5 * 0.95  # Numbers 5% smaller
        c.setFont("Helvetica", number_font_size)
        # Position GTIN number at aligned position
        c.drawString(number_start_x, right_y + gtin_y_shift, f"(01){product['gtin']}")
        right_y -= block_spacing
        
        # FIX 3 & 4: LOT block - NO "LOT" text, just icon (image8) and value
        if manufacturer_symbol_empty:
            # Move LOT icon 2pt up
            c.drawImage(manufacturer_symbol_empty, identifier_x, right_y - (icon_size_small * 0.55) + (2 / 72 * inch),
                       width=icon_size_small, height=icon_size_small,
                       preserveAspectRatio=True, mask="auto")
        
        c.setFont("Helvetica", number_font_size)
        # Position LOT value at aligned position
        c.drawString(number_start_x, right_y, f"(11){mfg_date}")
        right_y -= block_spacing
        
        # FIX 5: SN block - NO "SN" text, just icon and value, Size +6%, Shift +12pt X, 0pt Y
        sn_identifier_x = right_column_left + (2 / 72 * inch) + (12 / 72 * inch)  # Original +2pt, now +12pt more = +14pt X
        
        if sn_symbol:
            c.drawImage(sn_symbol, sn_identifier_x, right_y - (icon_size_small * 0.55),
                       width=icon_size_small, height=icon_size_small,
                       preserveAspectRatio=True, mask="auto")
        
        sn_font_size = number_font_size * 1.06  # +6% size
        c.setFont("Helvetica", sn_font_size)
        # Position SN value at aligned position from LOT (no Y shift from original right_y)
        sn_number_x = sn_identifier_x + max_label_width + icon_number_gap
        c.drawString(sn_number_x, right_y, f"(21){serial}")
        
        # QR CODE - 35% larger, positioned to align with CE logo right edge and EC REP text bottom, moved down 10pt
        qr_size_original = 0.72 * inch
        qr_size = qr_size_original * 1.35  # 35% larger
        qr_size_px = int(qr_size * 6.0)  # High resolution for maximum sharpness
        qr_img = generate_qr_code(udi_payload, target_px=qr_size_px)
        
        # Position QR code:
        # - Right edge aligned with CE mark right edge
        # - Bottom edge aligned with EC REP text end, then moved down 10pt
        qr_x = ce_mark_right_edge - qr_size
        qr_y = ec_rep_text_end_y - (10 / 72 * inch)  # Move down 10pt
        
        c.drawImage(qr_img, qr_x, qr_y, 
                   width=qr_size, height=qr_size)
        
        # FIX 1: UDI - use image14.png icon next to QR code (no text)
        # Maintain the same distance from QR code, so it moves with the QR code
        udi_icon_y = qr_y + (qr_size / 2)
        udi_icon_size = 0.22 * inch * 0.90  # 10% smaller
        udi_qr_gap = 0.08 * inch  # Fixed gap between UDI and QR
        
        if udi_symbol:
            # Position UDI icon to the left of QR code, vertically centered, maintaining gap
            udi_icon_x = qr_x - udi_icon_size - udi_qr_gap
            c.drawImage(udi_symbol, udi_icon_x, udi_icon_y - (udi_icon_size / 2),
                       width=udi_icon_size, height=udi_icon_size,
                       preserveAspectRatio=True, mask="auto")

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
