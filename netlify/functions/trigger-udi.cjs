const jwt = require("jsonwebtoken");

exports.handler = async (event) => {
  const headers = {
    "Access-Control-Allow-Origin": "https://kleinmed-ag.github.io",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type"
  };

  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers };
  }

  try {
    const body = JSON.parse(event.body);

    // 🔑 Normalize PEM key (THIS IS CRITICAL)
    const privateKey = process.env.GITHUB_PRIVATE_KEY.replace(/\\n/g, "\n").trim();

    const now = Math.floor(Date.now() / 1000);

    // 1️⃣ Create GitHub App JWT
    const appJwt = jwt.sign(
      {
        iat: now - 60,
        exp: now + 600,
        iss: process.env.GITHUB_APP_ID
      },
      privateKey,
      { algorithm: "RS256" }
    );

    // 2️⃣ Exchange for installation token
    const tokenResp = await fetch(
      `https://api.github.com/app/installations/${process.env.GITHUB_INSTALLATION_ID}/access_tokens`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${appJwt}`,
          Accept: "application/vnd.github+json"
        }
      }
    );

    const tokenData = await tokenResp.json();

    if (!tokenResp.ok) {
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify(tokenData)
      };
    }

    // 3️⃣ Trigger workflow_dispatch
    const ghResp = await fetch(
      "https://api.github.com/repos/kleinmed-ag/gtin/actions/workflows/generate-udi.yml/dispatches",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${tokenData.token}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          ref: "main",
          inputs: body
        })
      }
    );

    if (!ghResp.ok) {
      const t = await ghResp.text();
      return { statusCode: ghResp.status, headers, body: t };
    }

    return { statusCode: 200, headers, body: "OK" };

  } catch (err) {
    console.error(err);
    return {
      statusCode: 500,
      headers,
      body: err.message
    };
  }
};
