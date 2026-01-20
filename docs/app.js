
const productDbUrl = "../data/product_db.yaml";

async function loadProducts() {
  const resp = await fetch(productDbUrl);
  const text = await resp.text();
  const lines = text.split("\n").filter(l => l.trim().startsWith("name:"));
  
  const select = document.getElementById("product");
  lines.forEach(l => {
    const name = l.replace("name:","").trim();
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  });
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
