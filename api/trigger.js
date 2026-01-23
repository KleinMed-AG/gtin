export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { product, gtin, mfg_date, serial_start, count } = req.body;

  try {
    const response = await fetch(
      'https://api.github.com/repos/KleinMed-AG/gtin/dispatches',
      {
        method: 'POST',
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'Authorization': `Bearer ${process.env.GITHUB_TOKEN}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          event_type: 'generate-labels',
          client_payload: { product, gtin, mfg_date, serial_start, count }
        })
      }
    );

    if (response.status === 204) {
      return res.status(200).json({ success: true });
    } else {
      return res.status(500).json({ error: 'Workflow failed to trigger' });
    }
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
