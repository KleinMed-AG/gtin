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

    # Layout parameters matching the original PNG precisely
    left_margin = 12 * mm
    top_margin = 12 * mm

    for i in range(count):
        serial = serial_start + i
        udi_payload = generate_udi_string(product["gtin"], mfg_date, serial)

        if i > 0:
            c.showPage()

        # Current Y position (starting from top)
        y_pos = PAGE_HEIGHT - top_margin

        # === LEFT COLUMN ===
        
        # Logo - Cumulative adjustments: Move LEFT -3pt more, UP -1pt more, Reduce -1.5% more
        if logo:
            logo_scale = 0.952 * 0.985  # Previous -4.8% * new -1.5% = -6.22% total
            logo_w = 130 * mm * logo_scale
            logo_h = 38 * mm * logo_scale
            logo_x = left_margin - 20 - 9 - 3  # Previous -29pt + new -3pt = -32pt total
            logo_y_offset = -3 - 1  # Previous -3pt + new -1pt = -4pt total
            c.drawImage(logo, logo_x, y_pos - logo_h + logo_y_offset,
                       width=logo_w, height=logo_h,
                       preserveAspectRatio=True, mask="auto")
            y_pos -= (logo_h + 5 * mm - logo_y_offset)

        # Product titles (4 languages) - Cumulative: Move LEFT -2pt more, UP -1.5pt more, Reduce -1% more
        title_font_size = 24 * 0.98 * 0.99  # Previous -2% * new -1% = -2.98% total
        title_x = left_margin - 5.5 - 2  # Previous -5.5pt + new -2pt = -7.5pt total
        title_y_offset = -2 - 1.5  # Previous -2pt + new -1.5pt = -3.5pt total
        y_pos += title_y_offset
        
        c.setFont("Helvetica-Bold", title_font_size)
        line_height = 9 * mm
        c.drawString(title_x, y_pos, product["name_de"])
        y_pos -= line_height
        c.drawString(title_x, y_pos, product["name_en"])
        y_pos -= line_height
        c.drawString(title_x, y_pos, product["name_fr"])
        y_pos -= line_height
        c.drawString(title_x, y_pos, product["name_it"])
        y_pos -= 12 * mm

        # Description (pain relief text) - Move LEFT -4.5pt, UP -3.5pt
        desc_x = left_margin - 4.5  # Move LEFT -4.5pt
        desc_y_offset = -3.5  # Move UP -3.5pt
        y_pos += desc_y_offset
        
        c.setFont("Helvetica", 16.5)
        desc_line_height = 6.75 * mm
        c.drawString(desc_x, y_pos, product["description_de"][:100])
        y_pos -= desc_line_height
        c.drawString(desc_x, y_pos, product["description_en"][:100])
        y_pos -= desc_line_height
        c.drawString(desc_x, y_pos, product["description_fr"][:100])
        y_pos -= desc_line_height
        c.drawString(desc_x, y_pos, product["description_it"][:100])
        y_pos -= 22.5 * mm

        # Manufacturer block - Cumulative: Move RIGHT +5.5pt more, UP -3pt more, Reduce -4% more
        mfr_scale = 0.94 * 0.96  # Previous -6% * new -4% = -9.76% total
        mfr_x_offset = 10 + 5.5  # Previous +10pt + new +5.5pt = +15.5pt total
        mfr_y_offset = -7 - 3  # Previous -7pt + new -3pt = -10pt total
        y_pos += mfr_y_offset
        mfr_y = y_pos
        
        if manufacturer_symbol:
            icon_size = 20 * mm * mfr_scale
            c.drawImage(manufacturer_symbol, left_margin + mfr_x_offset, mfr_y - icon_size,
                       width=icon_size, height=icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        # Text with reduced scale
        mfr_font_size = 16.5 * mfr_scale
        c.setFont("Helvetica", mfr_font_size)
        text_x = left_margin + 24 * mm * mfr_scale + mfr_x_offset
        c.drawString(text_x, mfr_y, product["manufacturer"]["name"])
        mfr_y -= 6.75 * mm
        c.setFont("Helvetica", mfr_font_size)
        c.drawString(text_x, mfr_y, product["manufacturer"]["address_line1"])
        mfr_y -= 6.75 * mm
        c.drawString(text_x, mfr_y, product["manufacturer"]["address_line2"])
        y_pos = mfr_y - 12 * mm

        # EC REP block - Cumulative: Move RIGHT +4pt more, UP -2pt more, Reduce -2% more
        ec_scale = 0.965 * 0.98  # Previous -3.5% * new -2% = -5.43% total
        ec_x_offset = 8 + 4  # Previous +8pt + new +4pt = +12pt total
        ec_y_offset = -5 - 2  # Previous -5pt + new -2pt = -7pt total
        y_pos += ec_y_offset
        ec_y = y_pos
        
        if ec_rep_symbol:
            icon_size = 40 * mm * ec_scale
            c.drawImage(ec_rep_symbol, left_margin + ec_x_offset, ec_y - icon_size,
                       width=icon_size, height=icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        # Text with reduced scale - align with manufacturer text
        ec_font_size = 16.5 * ec_scale
        c.setFont("Helvetica", ec_font_size)
        text_x_ec = left_margin + 24 * mm * mfr_scale + mfr_x_offset  # Use same alignment as manufacturer
        c.drawString(text_x_ec, ec_y, product["distributor"]["name"])
        ec_y -= 6.75 * mm
        c.setFont("Helvetica", ec_font_size)
        c.drawString(text_x_ec, ec_y, product["distributor"]["address_line1"])
        ec_y -= 6.75 * mm
        
        address_line2 = product["distributor"]["address_line2"]
        if "Lübeck" in address_line2 and "," not in address_line2:
            parts = address_line2.split()
            if len(parts) >= 3:
                address_line2 = f"{parts[0]} {parts[1]}, {' '.join(parts[2:])}"
        c.drawString(text_x_ec, ec_y, address_line2)

        # === RIGHT COLUMN ===
        
        right_y = PAGE_HEIGHT - top_margin

        # Top symbols row - Cumulative: Move LEFT -2pt more, UP -1pt more, Reduce -1.5% more
        symbol_scale = 0.955 * 0.985  # Previous -4.5% * new -1.5% = -5.93% total
        symbol_x_offset = -7.5 - 2  # Previous -7.5pt + new -2pt = -9.5pt total
        symbol_y_offset = -2.5 - 1  # Previous -2.5pt + new -1pt = -3.5pt total
        symbol_y = right_y - 2 * mm + symbol_y_offset
        
        # CE mark (rightmost)
        ce_size = 24 * mm * symbol_scale
        ce_x = PAGE_WIDTH - left_margin - ce_size + symbol_x_offset
        if ce_mark:
            c.drawImage(ce_mark, ce_x, symbol_y - ce_size,
                       width=ce_size, height=ce_size,
                       preserveAspectRatio=True, mask="auto")
        
        # MD symbol
        md_size = 24 * mm * symbol_scale
        md_x = ce_x - md_size - 6 * mm
        if md_symbol:
            c.drawImage(md_symbol, md_x, symbol_y - md_size,
                       width=md_size, height=md_size,
                       preserveAspectRatio=True, mask="auto")
        
        # Spec symbols (3-box strip) - keep existing size
        if spec_symbols:
            spec_w = 100 * mm
            spec_h = 24 * mm
            spec_x = md_x - spec_w - 6 * mm
            c.drawImage(spec_symbols, spec_x, symbol_y - spec_h,
                       width=spec_w, height=spec_h,
                       preserveAspectRatio=True, mask="auto")
        
        right_y -= 37.5 * mm

        # GTIN/LOT/SN blocks - Cumulative adjustments
        gtin_x_offset = -11 - 3.5  # Previous -11pt + new -3.5pt = -14.5pt total
        gtin_y_offset = -1.5 - 0.5  # Previous -1.5pt + new -0.5pt = -2pt total
        gtin_scale = 0.98 * 0.99  # Previous -2% * new -1% = -2.98% total
        
        label_col_x = PAGE_WIDTH - 155 * mm + gtin_x_offset  # GTIN label position
        value_col_x = label_col_x + 45 * mm  # Value position
        icon_col_x = label_col_x - 20 * mm   # Icon position
        
        # GTIN - Cumulative: Move LEFT -3.5pt more, UP -0.5pt more, Reduce -1% more
        gtin_font_size = 21 * gtin_scale
        c.setFont("Helvetica-Bold", gtin_font_size)
        gtin_label = "GTIN"
        c.drawString(label_col_x, right_y + gtin_y_offset, gtin_label)
        
        # Value
        c.setFont("Helvetica", 18)
        c.drawString(value_col_x, right_y + gtin_y_offset, f"(01){product['gtin']}")
        right_y -= 15 * mm
        
        # LOT with factory icon - Cumulative: Move RIGHT +2.5pt more, DOWN +4.5pt more, Increase +2% more
        lot_x_offset = 7 + 2.5  # Previous +7pt + new +2.5pt = +9.5pt total
        lot_y_offset = 9 + 4.5  # Previous +9pt + new +4.5pt = +13.5pt total
        lot_scale = 1.04 * 1.02  # Previous +4% * new +2% = +6.08% total
        
        icon_box_size = 16 * mm * lot_scale
        if manufacturer_symbol_empty:
            c.drawImage(manufacturer_symbol_empty, icon_col_x + lot_x_offset, right_y - icon_box_size/2 - 1.5*mm - lot_y_offset,
                       width=icon_box_size, height=icon_box_size,
                       preserveAspectRatio=True, mask="auto")
        c.setFont("Helvetica", 18)
        c.drawString(value_col_x + lot_x_offset, right_y - lot_y_offset, f"(11){mfg_date}")
        right_y -= 15 * mm
        
        # SN with IMAGE icon - Cumulative: Move RIGHT +2.5pt more, DOWN +4.5pt more, Increase +2% more
        if sn_symbol:
            sn_icon_size = 16 * mm * lot_scale
            c.drawImage(sn_symbol, icon_col_x + lot_x_offset, right_y - sn_icon_size/2 - 1.5*mm - lot_y_offset,
                       width=sn_icon_size, height=sn_icon_size,
                       preserveAspectRatio=True, mask="auto")
        
        c.setFont("Helvetica", 18)
        c.drawString(value_col_x + lot_x_offset, right_y - lot_y_offset, f"(21){serial}")

        # QR Code - Cumulative: Move RIGHT +6pt more, UP -3pt more, Reduce -6% more
        qr_scale = 0.89 * 0.94  # Previous -11% * new -6% = -16.34% total
        qr_x_offset = 17 + 6  # Previous +17pt + new +6pt = +23pt total
        qr_y_offset = -8 - 3  # Previous -8pt + new -3pt = -11pt total
        
        qr_size = 102 * mm * qr_scale
        qr_size_px = int(qr_size * 4)
        qr_img = generate_qr_code(udi_payload, target_px=qr_size_px)
        
        qr_x = PAGE_WIDTH - left_margin - qr_size + qr_x_offset
        qr_y = 12 * mm + qr_y_offset
        c.drawImage(qr_img, qr_x, qr_y,
                   width=qr_size, height=qr_size)
        
        # UDI with IMAGE icon - Cumulative: Move RIGHT +4.5pt more, UP -2.5pt more, Reduce -4.5% more
        udi_scale = 0.91 * 0.955  # Previous -9% * new -4.5% = -13.095% total
        udi_x_offset = 13 + 4.5  # Previous +13pt + new +4.5pt = +17.5pt total
        udi_y_offset = -6 - 2.5  # Previous -6pt + new -2.5pt = -8.5pt total
        
        if udi_symbol:
            udi_icon_size = 32 * mm * udi_scale
            udi_icon_x = qr_x - udi_icon_size - 9 * mm + udi_x_offset
            udi_icon_y = qr_y + (qr_size - udi_icon_size) / 2 + udi_y_offset
            c.drawImage(udi_symbol, udi_icon_x, udi_icon_y,
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
