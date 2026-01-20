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

    // Fill dropdown
    products.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = p.name;
      productSelect.appendChild(opt);
    });

    // Prefill serial number
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

  const product = document.getElementById("product").value;
  const date = document.getElementById("date").value;
  const serialStart = document.getElementById("serialStart").value;
  const count = document.getElementById("count").value;

  const payload = {
    ref: "main",
    inputs: {
      product,
      date,
      serial_start: serialStart,
      count
    }
  };

  const response = await fetch(
    "https://api.github.com/repos/kleinmed-ag/gtin/actions/workflows/generate-udi.yml/dispatches",
    {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );

  if (response.ok) {
    document.getElementById("output").textContent =
      "UDI Erzeugung gestartet! GitHub Action läuft.";
  } else {
    document.getElementById("output").textContent =
      "Fehler: " + response.status + " " + response.statusText;
  }
});
