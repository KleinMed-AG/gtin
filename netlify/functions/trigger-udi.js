export default async (req) => {
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

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

  return new Response(
    ghResp.ok ? "OK" : "GitHub Error",
    { status: ghResp.status }
  );
};
