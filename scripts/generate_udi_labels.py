#!/usr/bin/env python3
import argparse
import csv
import os
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import inch, A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
import json

# A4 landscape dimensions
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)  # 11.69 x 8.27 inches (297mm x 210mm)

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
    """Create PDF with A4 landscape pages"""
    c = canvas.Canvas(output_file, pagesize=landscape(A4))

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

    # Global scale factor for A4 landscape
    GLOBAL_SCALE = 1.08  # Apply to all elements for proper density

    # Layout parameters for A4 landscape
    left_margin = 0.5 * inch  # Increased for A4
    top_margin = 0.5 * inch   # Increased for A4
    right_margin = 0.5 * inch # Increased for A4
    bottom_margin = 0.5 * inch # Increased for A4
    
    # Two-column grid
    usable_width = PAGE_WIDTH - left_margin - right_margin
    left_column_width = usable_width * 0.62
    column_gap = 0.10 * inch
    right_column_left = left_margin + left_column_width + column_gap

    for i in range(count):
        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        if i > 0:
            c.showPage()
            c.setPageSize(landscape(A4))

        # === LEFT COLUMN ===
        left_y = PAGE_HEIGHT - top_margin
        
        # Logo - +42% scale (1.58 * 1.42 = 2.24), +16pt X, +7.1pt Y
        if logo:
            logo_base_scale = 1.58 * 1.42 * GLOBAL_SCALE  # Previous adjustments * new scale * global
            logo_w = 0.86 * inch * logo_base_scale
            logo_h = 0.25 * inch * logo_base_scale
            logo_x = left_margin + (6 / 72 * inch) + 16  # Previous +6pt + new +16pt
            logo_y_shift = (4 / 72 * inch) + 7.1  # Previous +4pt + new +7.1pt
            c.drawImage(logo, logo_x, left_y - logo_h + logo_y_shift, 
                       width=logo_w, height=logo_h,
                       preserveAspectRatio=True, mask="auto")
            left_y -= (logo_h + 0.16 * inch - logo_y_shift)
        
        # Product title block - +18% font scale, +18.5pt X, +12.5pt Y, +10% line spacing
        product_name_font_size = 5 * 1.03 * 1.18 * GLOBAL_SCALE  # Previous * new +18% * global
        product_name_y_shift = (8 / 72 * inch) + 12.5  # Previous +8pt + new +12.5pt
        product_name_x_shift = 18.5  # +18.5pt X
        left_y += product_name_y_shift
        
        c.setFont("Helvetica-Bold", product_name_font_size)
        product_line_spacing = 6 * 1.10  # +10% line spacing
        c.drawString(left_margin + product_name_x_shift, left_y, product["name_de"])
        left_y -= product_line_spacing
        c.drawString(left_margin + product_name_x_shift, left_y, product["name_en"])
        left_y -= product_line_spacing
        c.drawString(left_margin + product_name_x_shift, left_y, product["name_fr"])
        left_y -= product_line_spacing
        c.drawString(left_margin + product_name_x_shift, left_y, product["name_it"])
        left_y -= 8
        
        # Indication paragraph - +14% font scale, +19.4pt X, +16.7pt Y, +8% line spacing
        description_font_size = 4 * 1.02 * 1.14 * GLOBAL_SCALE  # Previous * new +14% * global
        description_y_shift = (6 / 72 * inch) + 16.7  # Previous +6pt + new +16.7pt
        description_x_shift = 19.4  # +19.4pt X
        left_y += description_y_shift
        
        c.setFont("Helvetica", description_font_size)
        line_spacing = 5.5 * 1.08  # +8% line spacing
        c.drawString(left_margin + description_x_shift, left_y, product["description_de"][:80])
        left_y -= line_spacing
        c.drawString(left_margin + description_x_shift, left_y, product["description_en"][:80])
        left_y -= line_spacing
        c.drawString(left_margin + description_x_shift, left_y, product["description_fr"][:80])
        left_y -= line_spacing
        c.drawString(left_margin + description_x_shift, left_y, product["description_it"][:80])
        left_y -= 14
        
        # Manufacturer block - +12% font scale, +13.5pt X, +19.6pt Y
        icon_text_gap = 0.04 * inch
        left_margin_adjusted_mfr = left_margin + (15 / 72 * inch) - (4 / 72 * inch) + 13.5  # Previous adjustments + new +13.5pt X
        manufacturer_y_shift = (6 / 72 * inch) + 19.6  # Previous +6pt + new +19.6pt Y
        
        # Calculate text block height (3 lines: 6.5 + 6 + 6 = 18.5pt spacing)
        manufacturer_text_height = 18.5
        manufacturer_icon_size = (manufacturer_text_height / 72 * inch) * 0.85 * 0.98 * GLOBAL_SCALE  # Previous * global
        
        left_y += manufacturer_y_shift  # Apply Y shift
        text_x = left_margin_adjusted_mfr + manufacturer_icon_size + icon_text_gap
        manufacturer_start_y = left_y
        
        # Font size: +12% scale
        manufacturer_font_size = 4 * 0.98 * 1.12 * GLOBAL_SCALE  # Previous * new +12% * global
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
        
        # EC REP block - +12% font scale, +15.2pt X, +21.4pt Y
        left_margin_adjusted_ec = left_margin + (9 / 72 * inch) + 15.2  # Previous +9pt + new +15.2pt X
        ec_rep_y_shift = 21.4  # +21.4pt Y
        ec_rep_text_height = 12.5
        ec_rep_icon_size = (ec_rep_text_height / 72 * inch) * 1.75 * GLOBAL_SCALE  # Previous * global
        
        left_y += ec_rep_y_shift  # Apply Y shift
        text_x = left_margin_adjusted_ec + ec_rep_icon_size + icon_text_gap
        ec_rep_start_y = left_y
        
        # Font size: +12% scale
        ec_rep_font_size = 4 * 0.98 * 1.12 * GLOBAL_SCALE  # Previous * new +12% * global
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
        right_y = PAGE_HEIGHT - top_margin
        
        # Regulatory symbols - MD and CE: +22% scale, -14.3pt X, +3.6pt Y
        symbol_row_y = right_y - 0.02 * inch - (6 / 72 * inch) + 3.6  # Previous -6pt + new +3.6pt Y
        symbol_base_scale = 1.25 * 1.22 * GLOBAL_SCALE  # Previous 25% * new +22% * global
        symbol_size = 0.13 * inch * symbol_base_scale
        symbol_spacing = 0.04 * inch
        
        current_x = PAGE_WIDTH - right_margin - symbol_size - 14.3  # -14.3pt X
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
        
        # Spec symbols - +20% scale (1.45 * 1.20 = 1.74), -20.2pt X, +5.4pt Y
        if spec_symbols:
            spec_base_scale = 1.45 * 1.20 * GLOBAL_SCALE  # Previous * new +20% * global
            spec_w = 1.12 * inch * spec_base_scale
            spec_h = 0.16 * inch * spec_base_scale
            spec_x = current_x - spec_w + (15 / 72 * inch) - 20.2  # Previous +15pt + new -20.2pt X
            spec_y_shift = 5.4  # +5.4pt Y
            c.drawImage(spec_symbols, spec_x, symbol_row_y - 0.13 * inch * 1.25 - spec_y_shift,
                       width=spec_w, height=spec_h,
                       preserveAspectRatio=True, mask="auto")
        
        right_y -= 0.28 * inch
        
        # Move entire GTIN/LOT/SN block 10pt down (was 3pt, now 7pt more)
        right_y -= (10 / 72 * inch)
        
        # GTIN/LOT/SN blocks
        block_spacing = 11  # Increased from 10 to 11 (1pt more spacing)
        identifier_base_x = right_column_left + (2 / 72 * inch) + (4 / 72 * inch) - 25.3  # Previous adjustments + new -25.3pt X
        udi_icon_size = 0.22 * inch * 0.90 * GLOBAL_SCALE  # Previous * global
        icon_size_small = udi_icon_size
        icon_number_gap = 0.05 * inch + (1 / 72 * inch)
        
        # GTIN: +10% font scale, -25.3pt X, +6.5pt Y
        gtin_font_size = 6.5 * 0.85 * 1.10 * 1.10 * GLOBAL_SCALE  # Previous * old +10% * new +10% * global
        gtin_y_shift = (-2 / 72 * inch) + 6.5  # Previous -2pt + new +6.5pt Y
        c.setFont("Helvetica-Bold", gtin_font_size)
        gtin_label_width = c.stringWidth("GTIN", "Helvetica-Bold", gtin_font_size)
        
        max_label_width = max(gtin_label_width, icon_size_small)
        number_start_x = identifier_base_x + max_label_width + icon_number_gap
        
        c.setFont("Helvetica-Bold", gtin_font_size)
        c.drawString(identifier_base_x, right_y + gtin_y_shift, "GTIN")
        
        number_font_size = 5 * 0.95 * GLOBAL_SCALE  # Previous * global
        c.setFont("Helvetica", number_font_size)
        c.drawString(number_start_x, right_y + gtin_y_shift, f"(01){product['gtin']}")
        right_y -= block_spacing
        
        # LOT block: +15% icon scale, +10% text scale, -26.1pt X, +11.9pt Y
        lot_identifier_x = right_column_left + (2 / 72 * inch) - 26.1  # -26.1pt X
        lot_y_shift = 11.9  # +11.9pt Y
        lot_icon_size = icon_size_small * 1.15  # +15% icon scale
        
        if manufacturer_symbol_empty:
            c.drawImage(manufacturer_symbol_empty, lot_identifier_x, right_y - (lot_icon_size * 0.55) + (2 / 72 * inch) + lot_y_shift,
                       width=lot_icon_size, height=lot_icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        lot_font_size = number_font_size * 1.10  # +10% text scale
        c.setFont("Helvetica", lot_font_size)
        lot_number_x = lot_identifier_x + max_label_width + icon_number_gap
        c.drawString(lot_number_x, right_y + lot_y_shift, f"(11){mfg_date}")
        right_y -= block_spacing
        
        # SN block: +12% scale, -26.1pt X, +16.7pt Y
        sn_identifier_x = right_column_left + (2 / 72 * inch) + (12 / 72 * inch) - 26.1  # Previous adjustments + new -26.1pt X
        sn_y_shift = 16.7  # +16.7pt Y
        sn_icon_size = icon_size_small * 1.12  # +12% icon scale
        
        if sn_symbol:
            c.drawImage(sn_symbol, sn_identifier_x, right_y - (sn_icon_size * 0.55) + sn_y_shift,
                       width=sn_icon_size, height=sn_icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        sn_font_size = number_font_size * 1.06 * 1.12  # Previous +6% * new +12%
        c.setFont("Helvetica", sn_font_size)
        sn_number_x = sn_identifier_x + max_label_width + icon_number_gap
        c.drawString(sn_number_x, right_y + sn_y_shift, f"(21){serial}")
        
        # QR CODE: +28% scale, -30.3pt X, +19pt Y
        qr_size_original = 0.72 * inch
        qr_base_scale = 1.35 * 1.28 * GLOBAL_SCALE  # Previous 35% * new +28% * global
        qr_size = qr_size_original * qr_base_scale
        qr_size_px = int(qr_size * 6.0)  # High resolution for maximum sharpness
        qr_img = generate_qr_code(udi_payload, target_px=qr_size_px)
        
        # Position: -30.3pt X, +19pt Y
        qr_x = ce_mark_right_edge - qr_size - 30.3
        qr_y = ec_rep_text_end_y - (10 / 72 * inch) + 19.0  # Previous -10pt + new +19pt Y
        
        c.drawImage(qr_img, qr_x, qr_y, 
                   width=qr_size, height=qr_size)
        
        # UDI label: +20% scale, -27.8pt X, +17.9pt Y
        udi_icon_y = qr_y + (qr_size / 2)
        udi_base_scale = 0.90 * 1.20 * GLOBAL_SCALE  # Previous 90% * new +20% * global
        udi_icon_size = 0.22 * inch * udi_base_scale
        udi_qr_gap = 0.08 * inch
        
        if udi_symbol:
            udi_icon_x = qr_x - udi_icon_size - udi_qr_gap - 27.8  # -27.8pt X
            udi_icon_y_adjusted = udi_icon_y + 17.9  # +17.9pt Y
            c.drawImage(udi_symbol, udi_icon_x, udi_icon_y_adjusted - (udi_icon_size / 2),
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
