export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { run_id, artifact_name } = req.query;

  if (!run_id) {
    return res.status(400).json({ error: 'run_id is required' });
  }

  try {
    // Get artifacts for this run
    const artifactsResponse = await fetch(
      `https://api.github.com/repos/KleinMed-AG/gtin/actions/runs/${run_id}/artifacts`,
      {
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'Authorization': `Bearer ${process.env.GITHUB_TOKEN}`,
          'User-Agent': 'UDI-Generator'
        }
      }
    );

    if (!artifactsResponse.ok) {
      throw new Error('Failed to fetch artifacts');
    }

    const artifactsData = await artifactsResponse.json();
    
    if (!artifactsData.artifacts || artifactsData.artifacts.length === 0) {
      return res.status(404).json({ error: 'No artifacts found' });
    }

    // Get the first artifact (or filter by name if provided)
    let artifact = artifactsData.artifacts[0];
    if (artifact_name) {
      artifact = artifactsData.artifacts.find(a => a.name === artifact_name) || artifact;
    }

    // Download the artifact
    const downloadResponse = await fetch(artifact.archive_download_url, {
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': `Bearer ${process.env.GITHUB_TOKEN}`,
        'User-Agent': 'UDI-Generator'
      }
    });

    if (!downloadResponse.ok) {
      throw new Error('Failed to download artifact');
    }

    // Get the artifact data
    const artifactBuffer = await downloadResponse.arrayBuffer();

    // Set headers for file download
    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename="${artifact.name}.zip"`);
    res.setHeader('Content-Length', artifactBuffer.byteLength);

    return res.status(200).send(Buffer.from(artifactBuffer));

  } catch (error) {
    console.error('Download error:', error);
    return res.status(500).json({ error: error.message });
  }
}
