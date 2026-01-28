#!/usr/bin/env python3
import argparse
import qrcode
import csv
import os
from reportlab.lib.pagesizes import inch
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image

# Label dimensions: 3 inches x 2 inches (7.62cm x 5.08cm)
LABEL_WIDTH = 3 * inch
LABEL_HEIGHT = 2 * inch

def generate_udi_string(gtin, mfg_date, serial):
    """Generate UDI string in GS1 format"""
    return f"(01){gtin}(11){mfg_date}(21){serial}"

def generate_qr_code(data, size=200):
    """Generate QR code image"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return ImageReader(buffer)

def load_image_safe(filepath):
    """Load image if it exists, return None otherwise"""
    if os.path.exists(filepath):
        try:
            return ImageReader(filepath)
        except Exception as e:
            print(f"Warning: Could not load {filepath}: {e}")
            return None
    return None

def create_label_pdf(product_data, mfg_date, serial_start, count, output_file):
    """Create PDF with UDI labels - matching exact layout with all symbols"""
    c = canvas.Canvas(output_file, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))
    
    # Load all images
    logo = load_image_safe('assets/image1.png')  # BioRelax Logo
    ce_mark = load_image_safe('assets/image2.png')  # CE Mark
    md_symbol = load_image_safe('assets/image3.png')  # MD Symbol
    manufacturer_symbol = load_image_safe('assets/image6.png')  # Factory Symbol (Filled)
    ec_rep_symbol = load_image_safe('assets/image10.png')  # EC REP Symbol
    sn_symbol = load_image_safe('assets/image12.png')  # SN Symbol
    udi_symbol = load_image_safe('assets/image14.png')  # UDI Symbol
    bottom_symbols = load_image_safe('assets/Screenshot 2026-01-28 100951.png')  # Temp/Safety/Instructions
    
    for i in range(count):
        serial = serial_start + i
        udi_string = generate_udi_string(product_data['gtin'], mfg_date, serial)
        
        if i > 0:
            c.showPage()
        
        c.setPageSize((LABEL_WIDTH, LABEL_HEIGHT))
        
        # Margins
        left_margin = 0.15 * inch
        top_margin = 0.12 * inch
        right_margin = 0.15 * inch
        
        # Starting Y position from top
        y = LABEL_HEIGHT - top_margin
        
        # === TOP LEFT: Logo ===
        if logo:
            logo_width = 0.7 * inch
            logo_height = 0.2 * inch
            c.drawImage(logo, left_margin, y - logo_height, 
                       width=logo_width, height=logo_height, 
                       preserveAspectRatio=True, mask='auto')
            y -= (logo_height + 2)
        
        # === TOP RIGHT: CE Mark and MD Symbol ===
        top_right_y = LABEL_HEIGHT - top_margin - 0.05 * inch
        symbol_size = 0.15 * inch
        right_x = LABEL_WIDTH - right_margin - symbol_size
        
        if ce_mark:
            c.drawImage(ce_mark, right_x, top_right_y, 
                       width=symbol_size, height=symbol_size,
                       preserveAspectRatio=True, mask='auto')
        
        if md_symbol:
            c.drawImage(md_symbol, right_x - symbol_size - 0.05 * inch, top_right_y,
                       width=symbol_size, height=symbol_size,
                       preserveAspectRatio=True, mask='auto')
        
        # === MULTILINGUAL DESCRIPTIONS ===
        y -= 2
        c.setFont("Helvetica", 6.5)
        line_height = 7.5
        
        c.drawString(left_margin, y, product_data['description_de'])
        y -= line_height
        c.drawString(left_margin, y, product_data['description_en'])
        y -= line_height
        c.drawString(left_margin, y, product_data['description_fr'])
        y -= line_height
        c.drawString(left_margin, y, product_data['description_it'])
        y -= line_height + 3
        
        # === LEFT COLUMN: Manufacturer Info ===
        left_col_x = left_margin
        
        # Manufacturer symbol + name
        if manufacturer_symbol:
            symbol_h = 0.12 * inch
            c.drawImage(manufacturer_symbol, left_col_x, y - symbol_h,
                       width=0.12 * inch, height=symbol_h,
                       preserveAspectRatio=True, mask='auto')
            text_x = left_col_x + 0.14 * inch
        else:
            text_x = left_col_x
        
        c.setFont("Helvetica-Bold", 7)
        c.drawString(text_x, y - 0.08 * inch, product_data['manufacturer']['name'])
        y -= 8
        
        c.setFont("Helvetica", 6)
        c.drawString(text_x, y, product_data['manufacturer']['address_line1'])
        y -= 7
        c.drawString(text_x, y, product_data['manufacturer']['address_line2'])
        y -= 10
        
        # Product names (4 languages)
        c.setFont("Helvetica-Bold", 6)
        c.drawString(left_col_x, y, product_data['name_de'])
        y -= 7
        
        c.setFont("Helvetica", 6)
        c.drawString(left_col_x, y, product_data['name_en'])
        y -= 7
        c.drawString(left_col_x, y, product_data['name_fr'])
        y -= 7
        c.drawString(left_col_x, y, product_data['name_it'])
        y -= 10
        
        # EC REP symbol + Distributor
        if ec_rep_symbol:
            symbol_h = 0.12 * inch
            c.drawImage(ec_rep_symbol, left_col_x, y - symbol_h,
                       width=0.12 * inch, height=symbol_h,
                       preserveAspectRatio=True, mask='auto')
            text_x = left_col_x + 0.14 * inch
        else:
            text_x = left_col_x
        
        c.setFont("Helvetica-Bold", 6)
        c.drawString(text_x, y - 0.05 * inch, product_data['distributor']['name'])
        y -= 7
        
        c.setFont("Helvetica", 6)
        c.drawString(text_x, y, product_data['distributor']['address_line1'])
        y -= 7
        c.drawString(text_x, y, product_data['distributor']['address_line2'])
        
        # === CENTER COLUMN: UDI Data ===
        center_x = LABEL_WIDTH / 2 - 0.4 * inch
        center_y_start = LABEL_HEIGHT - top_margin - 0.25 * inch - (4 * line_height)
        
        # SN Symbol + Serial Number
        udi_y = center_y_start
        if sn_symbol:
            symbol_size = 0.13 * inch
            c.drawImage(sn_symbol, center_x - 0.15 * inch, udi_y - 0.08 * inch,
                       width=symbol_size, height=symbol_size,
                       preserveAspectRatio=True, mask='auto')
        
        c.setFont("Helvetica", 9)
        serial_text = f"(21){serial}"
        c.drawString(center_x, udi_y, serial_text)
        
        # UDI Symbol + GTIN
        udi_y -= 13
        if udi_symbol:
            symbol_size = 0.13 * inch
            c.drawImage(udi_symbol, center_x - 0.15 * inch, udi_y - 0.08 * inch,
                       width=symbol_size, height=symbol_size,
                       preserveAspectRatio=True, mask='auto')
        
        gtin_text = f"(01){product_data['gtin']}"
        c.drawString(center_x, udi_y, gtin_text)
        
        # Manufacturing date
        udi_y -= 13
        mfg_text = f"(11){mfg_date}"
        c.drawString(center_x, udi_y, mfg_text)
        
        # GTIN label
        udi_y -= 16
        c.setFont("Helvetica-Bold", 8)
        c.drawString(center_x, udi_y, "GTIN")
        
        # === BOTTOM CENTER: Symbols (Temp/Safety/Instructions) ===
        if bottom_symbols:
            symbol_width = 1.0 * inch
            symbol_height = 0.15 * inch
            bottom_y = 0.18 * inch
            symbol_x = center_x - 0.15 * inch
            c.drawImage(bottom_symbols, symbol_x, bottom_y,
                       width=symbol_width, height=symbol_height,
                       preserveAspectRatio=True, mask='auto')
        else:
            # Fallback to text if image not available
            bottom_info_y = 0.22 * inch
            c.setFont("Helvetica", 8)
            temp_height_text = f"{product_data['temp_min']}  {product_data['height']}"
            c.drawString(center_x - 0.1 * inch, bottom_info_y, temp_height_text)
            c.drawString(center_x + 0.75 * inch, bottom_info_y, product_data['temp_max'])
        
        # === RIGHT SIDE: QR Code ===
        qr_size = 1.15 * inch
        qr_x = LABEL_WIDTH - qr_size - 0.12 * inch
        qr_y = (LABEL_HEIGHT - qr_size) / 2 + 0.05 * inch
        
        qr_img = generate_qr_code(udi_string, size=int(qr_size * 2.5))
        c.drawImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)
    
    c.save()
    print(f"✓ PDF created: {output_file}")
    print(f"✓ Generated {count} labels (Serial {serial_start}-{serial_start + count - 1})")

def create_csv_file(product_data, mfg_date, serial_start, count, output_file):
    """Create CSV file matching the spreadsheet structure"""
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        writer.writerow([
            'AI - GTIN',
            'Artikelnummer/GTIN',
            'Name',
            'Grund-einheit',
            'SN/LOT',
            'Kurztext I',
            'Warengruppe',
            'AI - Herstelldatum',
            'Herstelldatum',
            'AI - SN',
            'Seriennummer',
            'UDI',
            'GTIN-Etikett',
            'Herstelldatum-Ettkett',
            'Seriennummer-Etikett',
            'QR',
            'QR-Code'
        ])
        
        for i in range(count):
            serial = serial_start + i
            udi_string = generate_udi_string(product_data['gtin'], mfg_date, serial)
            qr_url = f"https://image-charts.com/chart?cht=qr&chs=250x250&chl={udi_string}"
            
            writer.writerow([
                '(01)',
                product_data['gtin'],
                product_data['name_de'],
                product_data['grundeinheit'],
                product_data['sn_lot_type'],
                product_data['kurztext'],
                product_data['warengruppe'],
                '(11)',
                mfg_date,
                '(21)',
                serial,
                udi_string,
                f"(01){product_data['gtin']}",
                f"(11){mfg_date}",
                f"(21){serial}",
                udi_string,
                qr_url
            ])
    
    print(f"✓ CSV created: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Generate UDI labels')
    parser.add_argument('--product-json', required=True, help='Product data as JSON string')
    parser.add_argument('--mfg-date', required=True, help='Manufacturing date (YYMMDD)')
    parser.add_argument('--serial-start', type=int, required=True, help='Starting serial number')
    parser.add_argument('--count', type=int, required=True, help='Number of labels')
    
    args = parser.parse_args()
    
    import json
    product_data = json.loads(args.product_json)
    
    os.makedirs('output', exist_ok=True)
    
    safe_name = product_data['name_de'].replace(' ', '_')[:30]
    base_filename = f"UDI_Klebe-Etiketten_{safe_name}_SN{args.serial_start}-SN{args.serial_start + args.count - 1}"
    pdf_file = f"output/{base_filename}.pdf"
    csv_file = f"output/{base_filename}.csv"
    
    create_label_pdf(
        product_data,
        args.mfg_date,
        args.serial_start,
        args.count,
        pdf_file
    )
    
    create_csv_file(
        product_data,
        args.mfg_date,
        args.serial_start,
        args.count,
        csv_file
    )

if __name__ == '__main__':
    main()
