export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { product_data, gtin, mfg_date, serial_start, count } = req.body;

  try {
    const response = await fetch(
      'https://api.github.com/repos/KleinMed-AG/gtin/dispatches',
      {
        method: 'POST',
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'Authorization': `Bearer ${process.env.GITHUB_TOKEN}`,
          'Content-Type': 'application/json',
          'User-Agent': 'UDI-Generator'
        },
        body: JSON.stringify({
          event_type: 'generate-labels',
          client_payload: { 
            product_data, 
            gtin, 
            mfg_date, 
            serial_start, 
            count 
          }
        })
      }
    );

    if (response.status === 204) {
      await new Promise(resolve => setTimeout(resolve, 2000));

      const runsResponse = await fetch(
        'https://api.github.com/repos/KleinMed-AG/gtin/actions/workflows/generate-labels.yml/runs?per_page=1',
        {
          headers: {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': `Bearer ${process.env.GITHUB_TOKEN}`,
            'User-Agent': 'UDI-Generator'
          }
        }
      );
      
      const runsData = await runsResponse.json();
      const run_id = runsData.workflow_runs?.[0]?.id;

      return res.status(200).json({ 
        success: true, 
        run_id: run_id,
        repo: 'KleinMed-AG/gtin'
      });
    } else {
      const errorText = await response.text();
      console.error('GitHub API error:', response.status, errorText);
      return res.status(500).json({ 
        error: 'Workflow failed to trigger',
        details: errorText 
      });
    }
  } catch (error) {
    console.error('Error:', error);
    return res.status(500).json({ error: error.message });
  }
}
