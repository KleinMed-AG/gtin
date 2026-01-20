import os
import json
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PRODUCT_DB = "docs/data/product_db.json"

with open(PRODUCT_DB, "r", encoding="utf-8") as f:
    product_db = json.load(f)

product_name = os.environ["INPUT_PRODUCT"]
date_yymmdd = os.environ["INPUT_DATE"]
serial_start = int(os.environ["INPUT_SERIAL_START"])
count = int(os.environ["INPUT_COUNT"])

if not date_yymmdd.isdigit() or len(date_yymmdd) != 6:
    raise ValueError("Ungültiges Datumsformat (YYMMDD erwartet)")

if count <= 0:
    raise ValueError("Anzahl Etiketten muss > 0 sein")

product = next(
    (p for p in product_db["products"] if p["name"] == product_name),
    None
)

if not product:
    raise ValueError(f"Produkt '{product_name}' nicht gefunden")

gtin = product["gtin"]

os.makedirs("output", exist_ok=True)

pdf_path = f"output/UDI_Labels_{product_name.replace(' ', '_')}.pdf"
c = canvas.Canvas(pdf_path, pagesize=A4)

def make_udi(gtin, date, sn):
    return f"(01){gtin}(11){date}(21){sn}"

for i in range(count):
    sn = serial_start + i
    udi = make_udi(gtin, date_yymmdd, sn)

    qr_path = f"output/qr_{sn}.png"
    qrcode.make(udi).save(qr_path)

    c.drawString(20, 800, f"Produkt: {product_name}")
    c.drawString(20, 780, f"GTIN: {gtin}")
    c.drawString(20, 760, f"Herstelldatum (AI11): {date_yymmdd}")
    c.drawString(20, 740, f"Seriennummer: {sn}")
    c.drawString(20, 720, f"UDI: {udi}")
    c.drawImage(qr_path, 350, 680, width=150, height=150)
    c.showPage()

    os.remove(qr_path)

c.save()

product["last_serial"] = serial_start + count - 1

with open(PRODUCT_DB, "w", encoding="utf-8") as f:
    json.dump(product_db, f, indent=2, ensure_ascii=False)

print(f"PDF erstellt: {pdf_path}")
