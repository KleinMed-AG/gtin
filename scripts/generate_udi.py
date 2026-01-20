
import yaml, os, glob
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from utils import load_product_data, make_udi

os.makedirs("output", exist_ok=True)

# latest job file
job_file = sorted(glob.glob("jobs/udi/*.yaml"))[-1]
job = yaml.safe_load(open(job_file))

prod = load_product_data(job["product"])
gtin = prod["gtin"]

date = job["date"]
serial_start = int(job["serial_start"])
count = job["count"]

pdf_path = f"output/{job['product']}_UDI_Labels.pdf"
c = canvas.Canvas(pdf_path, pagesize=A4)

for i in range(count):
    sn = serial_start + i
    udi = make_udi(gtin, date, sn)

    qr = qrcode.make(udi)
    qr_path = f"output/qr_{sn}.png"
    qr.save(qr_path)

    c.drawString(20, 800, f"Produkt: {job['product']}")
    c.drawString(20, 780, f"GTIN: {gtin}")
    c.drawString(20, 760, f"Datum (AI11): {date}")
    c.drawString(20, 740, f"Seriennummer: {sn}")
    c.drawString(20, 720, f"UDI: {udi}")

    c.drawImage(qr_path, 350, 680, width=150, height=150)
    c.showPage()

c.save()
