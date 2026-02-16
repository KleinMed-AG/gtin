#!/usr/bin/env python3
"""
UDI Label Generator for A4 Landscape - Anchor-Based Alignment System
Matches original PDF structural alignment exactly
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
    """Create A4 landscape label PDF with anchor-based alignment"""
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

    # === ANCHOR-BASED ALIGNMENT SYSTEM ===
    
    # Margins
    top_margin = 15 * mm
    bottom_margin = 15 * mm
    left_margin = 15 * mm
    right_margin = 15 * mm
    
    # ABSOLUTE CORRECTIONS APPLIED
    global_left_column_offset = -2  # Move entire text column LEFT -2pt
    
    # 1️⃣ Primary Left Vertical Anchor (L1)
    # ALL left text content aligns here
    L1 = left_margin + global_left_column_offset
    
    # 2️⃣ Icon Alignment Line (L2)  
    # Factory icon and EC REP box align here
    L2 = L1  # Icons start at same position as text
    
    # 3️⃣ Central Vertical Division (C1)
    # Right column data values align here
    C1 = PAGE_WIDTH * 0.60  # Approximately 60% across page
    
    # 4️⃣ QR Anchor Line (R1)
    # QR right edge aligns to page right margin
    R1 = PAGE_WIDTH - right_margin
    
    # Horizontal anchors
    # 5️⃣ Top Horizontal Line (T1)
    T1 = PAGE_HEIGHT - top_margin

    for i in range(count):
        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        if i > 0:
            c.showPage()

        y_pos = T1  # Start from top anchor

        # === TOP ROW: Logo and Symbols (aligned to T1) ===
        
        # KleinMed Logo - aligned with title/description text (L1), with corrections
        if logo:
            logo_w = 120 * mm
            logo_h = 35 * mm
            logo_x = L1 - 1.5  # Align with text below, correction: -1.5pt
            logo_y_offset = -0.5  # Correction: UP -0.5pt
            c.drawImage(logo, logo_x, y_pos - logo_h + logo_y_offset,
                       width=logo_w, height=logo_h,
                       preserveAspectRatio=True, mask="auto")
        
        # Symbol row - right aligned, ABSOLUTE CORRECTION: UP -1pt
        symbol_size = 22 * mm
        header_symbol_y_offset = -1  # ABSOLUTE: UP -1pt
        symbol_y = y_pos + header_symbol_y_offset
        symbol_x_offset = -1  # Previous correction
        
        # CE mark (rightmost, aligned to R1)
        ce_x = R1 - symbol_size + symbol_x_offset
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
        
        # Spec symbols (3-box strip)
        if spec_symbols:
            spec_w = 90 * mm
            spec_h = 22 * mm
            spec_x = md_x - spec_w - 5 * mm
            c.drawImage(spec_symbols, spec_x, symbol_y - spec_h,
                       width=spec_w, height=spec_h,
                       preserveAspectRatio=True, mask="auto")
        
        # Move down after logo/symbols
        y_pos -= (logo_h + 8 * mm - logo_y_offset)

        # === PRODUCT TITLES - aligned to L1 with corrections ===
        title_x = L1 - 1  # Correction: LEFT -1pt
        title_y_offset = -1  # Correction: UP -1pt
        y_pos += title_y_offset
        
        c.setFont("Helvetica-Bold", 23)
        title_line_height = 8.5 * mm
        c.drawString(title_x, y_pos, product["name_de"])
        y_pos -= title_line_height
        c.drawString(title_x, y_pos, product["name_en"])
        y_pos -= title_line_height
        c.drawString(title_x, y_pos, product["name_fr"])
        y_pos -= title_line_height
        c.drawString(title_x, y_pos, product["name_it"])
        y_pos -= 10 * mm

        # === DESCRIPTION PARAGRAPH - aligned to L1 with corrections ===
        desc_x = L1 - 1  # Correction: LEFT -1pt
        desc_y_offset = -1.5  # Correction: UP -1.5pt
        y_pos += desc_y_offset
        
        c.setFont("Helvetica", 16)
        desc_line_height = 6.5 * mm
        c.drawString(desc_x, y_pos, product["description_de"][:100])
        y_pos -= desc_line_height
        c.drawString(desc_x, y_pos, product["description_en"][:100])
        y_pos -= desc_line_height
        c.drawString(desc_x, y_pos, product["description_fr"][:100])
        y_pos -= desc_line_height
        c.drawString(desc_x, y_pos, product["description_it"][:100])
        y_pos -= 15 * mm

        # === MANUFACTURER BLOCK ===
        mfr_x_offset = 15 + 3  # Previous +15pt + correction +3pt = +18pt
        mfr_y_offset = -2  # Correction: UP -2pt
        y_pos += mfr_y_offset
        mfr_y = y_pos
        
        mfr_icon_size = 18 * mm
        # Text position
        mfr_text_x = L1 + mfr_x_offset
        # ABSOLUTE CORRECTION: Factory icon RIGHT +3pt
        factory_icon_offset = 3  # ABSOLUTE: RIGHT +3pt
        # Icon immediately to the left of text (reduced gap)
        mfr_icon_x = mfr_text_x - mfr_icon_size - 2 * mm + factory_icon_offset
        
        # Factory icon - immediately to left of text
        if manufacturer_symbol:
            c.drawImage(manufacturer_symbol, mfr_icon_x, mfr_y - mfr_icon_size,
                       width=mfr_icon_size, height=mfr_icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        # Text
        c.setFont("Helvetica", 15)
        c.drawString(mfr_text_x, mfr_y, product["manufacturer"]["name"])
        mfr_y -= 6 * mm
        c.drawString(mfr_text_x, mfr_y, product["manufacturer"]["address_line1"])
        mfr_y -= 6 * mm
        c.drawString(mfr_text_x, mfr_y, product["manufacturer"]["address_line2"])
        y_pos = mfr_y - 7 * mm  # Decreased from 10mm to 7mm (reduce spacing to EC REP)

        # === EC REP BLOCK ===
        ec_x_offset = 2.5  # Correction: RIGHT +2.5pt (added to alignment with manufacturer)
        ec_y_offset = -1.5  # Correction: UP -1.5pt
        y_pos += ec_y_offset
        ec_y = y_pos
        
        ec_icon_size = 36 * mm
        # Text aligned with manufacturer + correction
        ec_text_x = mfr_text_x + ec_x_offset
        # ABSOLUTE CORRECTION: EC REP box RIGHT +6pt
        ec_rep_icon_offset = 6  # ABSOLUTE: RIGHT +6pt
        # Icon immediately to the left of text (reduced gap)
        ec_icon_x = ec_text_x - ec_icon_size - 2 * mm + ec_rep_icon_offset
        
        # EC REP box - immediately to left of text
        if ec_rep_symbol:
            c.drawImage(ec_rep_symbol, ec_icon_x, ec_y - ec_icon_size,
                       width=ec_icon_size, height=ec_icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        # Text - aligned with manufacturer + correction
        c.setFont("Helvetica", 15)
        c.drawString(ec_text_x, ec_y, product["distributor"]["name"])
        ec_y -= 6 * mm
        c.drawString(ec_text_x, ec_y, product["distributor"]["address_line1"])
        ec_y -= 6 * mm
        
        address_line2 = product["distributor"]["address_line2"]
        if "Lübeck" in address_line2 and "," not in address_line2:
            parts = address_line2.split()
            if len(parts) >= 3:
                address_line2 = f"{parts[0]} {parts[1]}, {' '.join(parts[2:])}"
        c.drawString(ec_text_x, ec_y, address_line2)

        # === RIGHT COLUMN - Data aligned to C1 ===
        
        right_y = T1 - 35 * mm  # Start below symbols
        
        # Block moved RIGHT +15pt, with corrections
        block_x_offset = 15 - 1.5  # RIGHT +15pt, correction LEFT -1.5pt = +13.5pt total
        block_y_offset = -0.5  # Correction: UP -0.5pt
        right_y += block_y_offset
        
        right_spacing = 13 * mm + 4  # Original 13mm + 4pt increase
        
        # ABSOLUTE CORRECTION: Right data column LEFT -6.5pt
        right_data_column_offset = -6.5  # ABSOLUTE: LEFT -6.5pt
        
        # Numbers position
        data_value_x = C1 + 15 + block_x_offset + right_data_column_offset  # Apply absolute correction
        # Icons to the left with reduced gap
        icon_gap = 3 * mm  # Reduced gap between icon and number
        icon_x = data_value_x - 42 * mm  # Adjusted for reduced gap
        
        # GTIN
        c.setFont("Helvetica-Bold", 20)
        c.drawString(icon_x, right_y, "GTIN")
        c.setFont("Helvetica", 17)
        c.drawString(data_value_x, right_y, f"(01){product['gtin']}")
        right_y -= right_spacing  # Increased spacing
        
        # ABSOLUTE CORRECTION: Date + SN icon column RIGHT +6pt
        date_sn_icon_offset = 6  # ABSOLUTE: RIGHT +6pt
        
        # LOT with icon to left (reduced gap) + ABSOLUTE correction
        lot_icon_size = 17 * mm
        if manufacturer_symbol_empty:
            c.drawImage(manufacturer_symbol_empty, icon_x + date_sn_icon_offset, right_y - lot_icon_size/2,
                       width=lot_icon_size, height=lot_icon_size,
                       preserveAspectRatio=True, mask="auto")
        c.setFont("Helvetica", 17)
        c.drawString(data_value_x, right_y, f"(11){mfg_date}")
        right_y -= right_spacing  # Increased spacing
        
        # SN with icon to left (reduced gap) + ABSOLUTE correction
        sn_x_offset = 1.5  # Correction: RIGHT +1.5pt
        sn_y_offset = 2.5  # Correction: DOWN +2.5pt
        
        if sn_symbol:
            c.drawImage(sn_symbol, icon_x + date_sn_icon_offset + sn_x_offset, right_y - lot_icon_size/2 - sn_y_offset,
                       width=lot_icon_size, height=lot_icon_size,
                       preserveAspectRatio=True, mask="auto")
        c.setFont("Helvetica", 17)
        c.drawString(data_value_x + sn_x_offset, right_y - sn_y_offset, f"(21){serial}")

        # === QR CODE - right aligned to R1 ===
        # ABSOLUTE CORRECTIONS: RIGHT +5.5pt, UP -10.5pt
        qr_x_absolute_offset = 5.5  # ABSOLUTE: RIGHT +5.5pt
        qr_y_absolute_offset = -10.5  # ABSOLUTE: UP -10.5pt
        
        qr_x_offset = 2.5 + qr_x_absolute_offset  # Previous +2.5pt + absolute +8pt
        qr_y_offset = -1.5 + qr_y_absolute_offset  # Previous -1.5pt + absolute -10pt
        
        qr_size = 85 * mm
        qr_size_px = int(qr_size * 4)
        qr_img = generate_qr_code(udi_payload, target_px=qr_size_px)
        
        qr_x = R1 - qr_size + qr_x_offset
        qr_y = bottom_margin + qr_y_offset
        c.drawImage(qr_img, qr_x, qr_y,
                   width=qr_size, height=qr_size)
        
        # ABSOLUTE CORRECTION: UDI box RIGHT +4pt, UP -4.5pt
        udi_x_absolute_offset = 4  # ABSOLUTE: RIGHT +4pt
        udi_y_absolute_offset = -4.5  # ABSOLUTE: UP -4.5pt
        
        # UDI icon - to left of QR with corrections
        udi_x_offset = 2 + udi_x_absolute_offset  # Previous +2pt + absolute +4pt
        udi_y_offset = -1 + udi_y_absolute_offset  # Previous -1pt + absolute -4.5pt
        
        if udi_symbol:
            udi_size = 28 * mm
            udi_x = qr_x - udi_size - 8 * mm + udi_x_offset
            udi_y = qr_y + (qr_size - udi_size) / 2 + udi_y_offset
            c.drawImage(udi_symbol, udi_x, udi_y,
                       width=udi_size, height=udi_size,
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
