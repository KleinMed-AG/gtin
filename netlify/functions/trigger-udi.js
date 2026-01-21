export default async (req) => {
  const headers = {
    "Access-Control-Allow-Origin": "https://kleinmed-ag.github.io",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };

  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers });
  }

  if (req.method !== "POST") {
    return new Response("Method Not Allowed", {
      status: 405,
      headers
    });
  }

  try {
    const payload = await req.json();

    const ghResp = await fetch(
      "https://api.github.com/repos/kleinmed-ag/gtin/dispatches",
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${process.env.GITHUB_TOKEN}`,
          "Accept": "application/vnd.github+json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          event_type: "generate-udi",
          client_payload: payload
        })
      }
    );

    if (!ghResp.ok) {
      const text = await ghResp.text();
      return new Response(text, {
        status: ghResp.status,
        headers
      });
    }

    return new Response("OK", {
      status: 200,
      headers
    });

  } catch (err) {
    return new Response(err.message, {
      status: 500,
      headers
    });
  }
};
