#!/usr/bin/env python3
import argparse
import qrcode
import csv
import os
from reportlab.lib.pagesizes import inch
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from PIL import Image

# Label dimensions: 3 inches x 2 inches
LABEL_WIDTH = 3 * inch
LABEL_HEIGHT = 2 * inch

def generate_udi_string(gtin, mfg_date, serial):
    """Generate UDI string in GS1 format"""
    return f"(01){gtin}(11){mfg_date}(21){serial}"

def generate_qr_code(data, size=200):
    """Generate QR code image"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize to specific size
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return ImageReader(buffer)

def load_image_if_exists(filepath):
    """Load image if it exists, return None otherwise"""
    if os.path.exists(filepath):
        return ImageReader(filepath)
    return None

def create_label_pdf(product_data, mfg_date, serial_start, count, output_file):
    """Create PDF with UDI labels - one per page"""
    c = canvas.Canvas(output_file, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))
    
    # Try to load assets
    logo = load_image_if_exists('assets/kleinmed_logo.png')
    
    for i in range(count):
        serial = serial_start + i
        udi_string = generate_udi_string(product_data['gtin'], mfg_date, serial)
        
        if i > 0:
            c.showPage()
        
        # Set page size for each label
        c.setPageSize((LABEL_WIDTH, LABEL_HEIGHT))
        
        # Draw border (optional, for alignment during development)
        # c.rect(0, 0, LABEL_WIDTH, LABEL_HEIGHT)
        
        # Margins
        margin_left = 0.15 * inch
        margin_top = 0.15 * inch
        
        # === TOP SECTION: Multilingual Description ===
        y_position = LABEL_HEIGHT - margin_top
        
        c.setFont("Helvetica", 7)
        # German
        c.drawString(margin_left, y_position, product_data['description_de'])
        y_position -= 9
        # English
        c.drawString(margin_left, y_position, product_data['description_en'])
        y_position -= 9
        # French
        c.drawString(margin_left, y_position, product_data['description_fr'])
        y_position -= 9
        # Italian
        c.drawString(margin_left, y_position, product_data['description_it'])
        y_position -= 15
        
        # === LEFT SECTION: Company Info ===
        left_col_x = margin_left
        company_y = y_position
        
        # KleinMed AG Logo (if available)
        if logo:
            logo_width = 0.6 * inch
            logo_height = 0.3 * inch
            c.drawImage(logo, left_col_x, company_y - logo_height, 
                       width=logo_width, height=logo_height, preserveAspectRatio=True)
            company_y -= (logo_height + 5)
        
        # Manufacturer info
        c.setFont("Helvetica-Bold", 7)
        c.drawString(left_col_x, company_y, product_data['manufacturer']['name'])
        company_y -= 9
        c.setFont("Helvetica", 6)
        c.drawString(left_col_x, company_y, product_data['manufacturer']['address_line1'])
        company_y -= 8
        c.drawString(left_col_x, company_y, product_data['manufacturer']['address_line2'])
        company_y -= 12
        
        # Product names (multilingual)
        c.setFont("Helvetica-Bold", 6)
        c.drawString(left_col_x, company_y, product_data['name_de'])
        company_y -= 8
        c.setFont("Helvetica", 6)
        c.drawString(left_col_x, company_y, product_data['name_en'])
        company_y -= 8
        c.drawString(left_col_x, company_y, product_data['name_fr'])
        company_y -= 8
        c.drawString(left_col_x, company_y, product_data['name_it'])
        company_y -= 12
        
        # Distributor info
        c.setFont("Helvetica-Bold", 6)
        c.drawString(left_col_x, company_y, product_data['distributor']['name'])
        company_y -= 8
        c.setFont("Helvetica", 6)
        c.drawString(left_col_x, company_y, product_data['distributor']['address_line1'])
        company_y -= 8
        c.drawString(left_col_x, company_y, product_data['distributor']['address_line2'])
        
        # === CENTER SECTION: UDI Information ===
        center_x = LABEL_WIDTH / 2 - 0.3 * inch
        udi_y = y_position - 10
        
        c.setFont("Helvetica", 8)
        
        # Serial Number
        serial_text = f"(21){serial}"
        c.drawString(center_x, udi_y, serial_text)
        udi_y -= 12
        
        # GTIN
        gtin_text = f"(01){product_data['gtin']}"
        c.drawString(center_x, udi_y, gtin_text)
        udi_y -= 12
        
        # Manufacturing Date
        mfg_text = f"(11){mfg_date}"
        c.drawString(center_x, udi_y, mfg_text)
        udi_y -= 15
        
        # GTIN label
        c.setFont("Helvetica-Bold", 7)
        c.drawString(center_x, udi_y, "GTIN")
        
        # === BOTTOM SECTION: Temperature and Height ===
        bottom_y = 0.2 * inch
        c.setFont("Helvetica", 8)
        temp_text = f"{product_data['temp_min']}  {product_data['height']}"
        c.drawString(center_x, bottom_y + 10, temp_text)
        c.drawString(center_x + 0.7 * inch, bottom_y + 10, product_data['temp_max'])
        
        # === RIGHT SECTION: QR Code ===
        qr_size = 1.2 * inch
        qr_x = LABEL_WIDTH - qr_size - 0.15 * inch
        qr_y = (LABEL_HEIGHT - qr_size) / 2
        
        qr_img = generate_qr_code(udi_string, size=int(qr_size * 2))
        c.drawImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)
    
    c.save()
    print(f"✓ PDF created: {output_file}")
    print(f"✓ Generated {count} labels (Serial {serial_start}-{serial_start + count - 1})")

def create_csv_file(product_data, mfg_date, serial_start, count, output_file):
    """Create CSV file matching the spreadsheet structure"""
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header matching your spreadsheet
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
    
    # Generate filename with product name
    safe_name = product_data['name_de'].replace(' ', '_')[:30]
    base_filename = f"UDI_Klebe-Etiketten_{safe_name}_SN{args.serial_start}-SN{args.serial_start + args.count - 1}"
    pdf_file = f"output/{base_filename}.pdf"
    csv_file = f"output/{base_filename}.csv"
    
    # Generate both PDF and CSV
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
