document.addEventListener("DOMContentLoaded", loadProducts);

async function loadProducts() {
  try {
    const resp = await fetch("./data/product_db.json", { cache: "no-store" });

    if (!resp.ok) {
      throw new Error("Fehler beim Laden der Produktdaten: HTTP " + resp.status);
    }

    const db = await resp.json();
    const products = db.products;

    if (!products || products.length === 0) {
      throw new Error("Keine Produkte in product_db.json gefunden.");
    }

    const productSelect = document.getElementById("product");

    products.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = p.name;
      productSelect.appendChild(opt);
    });

    function updateSerial() {
      const p = products.find(x => x.name === productSelect.value);
      document.getElementById("serialStart").value = (p.last_serial || 0) + 1;
    }

    productSelect.addEventListener("change", updateSerial);
    updateSerial();

  } catch (err) {
    console.error(err);
    document.getElementById("output").textContent = err.message;
  }
}

document.getElementById("udiForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const payload = {
    product: document.getElementById("product").value,
    date: document.getElementById("date").value,
    serial_start: document.getElementById("serialStart").value,
    count: document.getElementById("count").value
  };

  const resp = await fetch("/.netlify/functions/trigger-udi", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  document.getElementById("output").textContent = resp.ok
    ? "UDI Job gestartet."
    : "Fehler beim Starten des UDI Jobs.";
});

  document.getElementById("output").textContent = response.ok
    ? "UDI Erzeugung gestartet! GitHub Action läuft."
    : `Fehler: ${response.status} ${response.statusText}`;
});
