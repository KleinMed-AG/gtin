import os
import json
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Path for product database
PRODUCT_DB = "data/product_db.json"

# Load product database
with open(PRODUCT_DB, "r", encoding="utf-8") as f:
    product_db = json.load(f)

# Read inputs from GitHub Actions
product_name = os.environ["INPUT_PRODUCT"]
date_yymmdd = os.environ["INPUT_DATE"]
serial_start = int(os.environ["INPUT_SERIAL_START"])
count = int(os.environ["INPUT_COUNT"])

# Lookup product info
products = product_db["products"]
product = next((p for p in products if p["name"] == product_name), None)

if not product:
    raise ValueError(f"Produkt '{product_name}' nicht gefunden in product_db.json")

gtin = product["gtin"]

# Output directory
os.makedirs("output", exist_ok=True)

# PDF output path
pdf_path = f"output/UDI_Labels_{product_name.replace(' ', '_')}.pdf"
c = canvas.Canvas(pdf_path, pagesize=A4)

def make_udi(gtin, date, sn):
    """
    UDI structure: (01)GTIN(11)YYMMDD(21)SERIAL
    """
    return f"(01){gtin}(11){date}(21){sn}"

for i in range(count):
    sn = serial_start + i
    udi = make_udi(gtin, date_yymmdd, sn)

    # QR Code erstellen
    qr_path = f"output/qr_{sn}.png"
    qr = qrcode.make(udi)
    qr.save(qr_path)

    # PDF Label
    c.drawString(20, 800, f"Produkt: {product_name}")
    c.drawString(20, 780, f"GTIN: {gtin}")
    c.drawString(20, 760, f"Herstelldatum (AI11): {date_yymmdd}")
    c.drawString(20, 740, f"Seriennummer: {sn}")
    c.drawString(20, 720, f"UDI: {udi}")

    c.drawImage(qr_path, 350, 680, width=150, height=150)
    c.showPage()

c.save()

print(f"PDF erstellt: {pdf_path}")
print("Fertig.")
