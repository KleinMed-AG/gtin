
const productDbUrl = "../data/product_db.yaml";


async function loadProducts() {
  const resp = await fetch("../data/product_db.yaml");
  const text = await resp.text();

  // YAML parsen
  const lines = text.split("\n");

  const productSelect = document.getElementById("product");

  let currentProduct = null;
  let products = [];

  for (let line of lines) {
    if (line.startsWith("  - name:")) {
      if (currentProduct) products.push(currentProduct);
      currentProduct = { name: line.split(":")[1].trim().replace(/"/g, "") };
    }
    if (line.includes("gtin:")) {
      currentProduct.gtin = line.split(":")[1].trim().replace(/"/g, "");
    }
    if (line.includes("last_serial:")) {
      currentProduct.last_serial = parseInt(line.split(":")[1].trim());
    }
  }
  if (currentProduct) products.push(currentProduct);

  // Select befüllen
  products.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.name;
    opt.textContent = p.name;
    productSelect.appendChild(opt);
  });

  // Auto-Start-SN
  productSelect.addEventListener("change", () => {
    const sel = products.find(p => p.name === productSelect.value);
    document.getElementById("serialStart").value = sel.last_serial + 1;
  });

  // Default: erstes Produkt auswählen
  const first = products[0];
  productSelect.value = first.name;
  document.getElementById("serialStart").value = first.last_serial + 1;
}

loadProducts();

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
