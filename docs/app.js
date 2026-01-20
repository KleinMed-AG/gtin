
const productDbUrl = "data/product_db.json";



async function loadProducts() {
  const output = document.getElementById("output");
  try {
    // fetch from inside docs
    const resp = await fetch("./data/product_db.json", { cache: "no-store" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status} while fetching product DB`);
    const db = await resp.json();

    const products = db.products || [];
    if (!Array.isArray(products) || products.length === 0) {
      throw new Error("Keine Produkte gefunden (leere products-Liste).");
    }

    const productSelect = document.getElementById("product");

    // fill the dropdown
    products.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = p.name;
      productSelect.appendChild(opt);
    });

    // helper to prefill serial = last_serial + 1
    function prefillSerial() {
      const selected = products.find(p => p.name === productSelect.value);
      if (!selected) return;
      const nextSerial = (parseInt(selected.last_serial, 10) || 0) + 1;
      document.getElementById("serialStart").value = nextSerial;
    }

    productSelect.addEventListener("change", prefillSerial);
    prefillSerial(); // initial prefill

    // (Optional) default date format = YYMMDD, user enters 6 digits
    const dateInput = document.getElementById("date");
    dateInput.placeholder = "YYMMDD"; // 6 digits as you requested
  } catch (err) {
    console.error(err);
    output.textContent = "Fehler beim Laden der Produktdaten: " + err.message;
  }
}

document.addEventListener("DOMContentLoaded", loadProducts);



document.getElementById("udiForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const product = document.getElementById("product").value;
  const date = document.getElementById("date").value;
  const serialStart = document.getElementById("serialStart").value;
  const count = document.getElementById("count").value;

  const yaml = `
product: "${product}"
date: "${date}"
serial_start: ${serialStart}
count: ${count}
operator: "GitHub Pages UI"
`;

  document.getElementById("output").textContent = yaml;

  const filename = `jobs/udi/job-${Date.now()}.yaml`;

  await fetch(filename, {
    method: "PUT",
    headers: {
      "Content-Type": "text/plain",
    },
    body: yaml,
  });

  alert("UDI Job erstellt! GitHub Actions startet jetzt automatisch.");
});
