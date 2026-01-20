
import yaml

def load_product_data(product_name):
    db = yaml.safe_load(open("data/product_db.yaml"))
    return next(p for p in db["products"] if p["name"] == product_name)

def make_udi(gtin, date, sn):
    return f"(01){gtin}(11){date}(21){sn}"
``
