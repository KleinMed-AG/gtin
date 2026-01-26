#!/usr/bin/env python3
import argparse
import qrcode
import csv
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO

def generate_udi_string(gtin, mfg_date, serial):
    """Generate UDI string in GS1 format"""
    return f"(01){gtin}(11){mfg_date}(21){serial:06d}"

def generate_qr_code(data):
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
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return ImageReader(buffer)

def create_csv_file(product, gtin, mfg_date, serial_start, count, output_file):
    """Create CSV file with serial numbers"""
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Product Name', 'GTIN', 'Manufacturing Date', 'Serial Number', 'UDI'])
        
        for i in range(count):
            serial = serial_start + i
            udi_string = generate_udi_string(gtin, mfg_date, serial)
            # Format date as YYYY-MM-DD for better readability
            formatted_date = f"20{mfg_date[:2]}-{mfg_date[2:4]}-{mfg_date[4:6]}"
            writer.writerow([product, gtin, formatted_date, f"{serial:06d}", udi_string])
    
    print(f"✓ CSV created: {output_file}")

def create_label_pdf(product, gtin, mfg_date, serial_start, count, output_file):
    """Create PDF with UDI labels"""
    c = canvas.Canvas(output_file, pagesize=A4)
    width, height = A4
    
    label_width = 80 * mm
    label_height = 50 * mm
    margin = 10 * mm
    
    labels_per_row = 2
    labels_per_col = 5
    
    for i in range(count):
        serial = serial_start + i
        udi_string = generate_udi_string(gtin, mfg_date, serial)
        
        if i > 0 and i % (labels_per_row * labels_per_col) == 0:
            c.showPage()
        
        label_on_page = i % (labels_per_row * labels_per_col)
        row = label_on_page // labels_per_row
        col = label_on_page % labels_per_row
        
        x = margin + col * (label_width + 5*mm)
        y = height - margin - (row + 1) * (label_height + 5*mm)
        
        c.rect(x, y, label_width, label_height)
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x + 5*mm, y + label_height - 8*mm, product[:40])
        
        c.setFont("Helvetica", 8)
        c.drawString(x + 5*mm, y + label_height - 14*mm, f"GTIN: {gtin}")
        c.drawString(x + 5*mm, y + label_height - 20*mm, f"MFG: 20{mfg_date[:2]}-{mfg_date[2:4]}-{mfg_date[4:6]}")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 5*mm, y + label_height - 26*mm, f"S/N: {serial:06d}")
        
        qr_img = generate_qr_code(udi_string)
        qr_size = 30 * mm
        c.drawImage(qr_img, x + label_width - qr_size - 5*mm, y + 5*mm, 
                    width=qr_size, height=qr_size)
        
        c.setFont("Helvetica", 6)
        c.drawString(x + 5*mm, y + 3*mm, udi_string[:50])
    
    c.save()
    print(f"✓ PDF created: {output_file}")
    print(f"✓ Generated {count} labels (Serial {serial_start:06d}-{serial_start + count - 1:06d})")

def main():
    parser = argparse.ArgumentParser(description='Generate UDI labels')
    parser.add_argument('--product', required=True)
    parser.add_argument('--gtin', required=True)
    parser.add_argument('--mfg-date', required=True)
    parser.add_argument('--serial-start', type=int, required=True)
    parser.add_argument('--count', type=int, required=True)
    
    args = parser.parse_args()
    
    os.makedirs('output', exist_ok=True)
    
    base_filename = f"UDI_{args.gtin}_{args.mfg_date}_{args.serial_start}"
    pdf_file = f"output/{base_filename}.pdf"
    csv_file = f"output/{base_filename}.csv"
    
    # Generate both PDF and CSV
    create_label_pdf(
        args.product,
        args.gtin,
        args.mfg_date,
        args.serial_start,
        args.count,
        pdf_file
    )
    
    create_csv_file(
        args.product,
        args.gtin,
        args.mfg_date,
        args.serial_start,
        args.count,
        csv_file
    )

if __name__ == '__main__':
    main()
