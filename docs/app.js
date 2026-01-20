
const productDbUrl = "../data/product_db.json";


async function loadProducts() {
  const resp = await fetch("../data/product_db.json");
  const db = await resp.json();
  const products = db.products;

  const productSelect = document.getElementById("product");

  // Dropdown füllen
  products.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.name;
    opt.textContent = p.name;
    productSelect.appendChild(opt);
  });

  // Auto Seriennummer +1
  function updateSerial() {
    const selected = products.find(p => p.name === productSelect.value);
    document.getElementById("serialStart").value = selected.last_serial + 1;
  }

  productSelect.addEventListener("change", updateSerial);

  // initial
  updateSerial();
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
