import jwt from "jsonwebtoken";
import crypto from "crypto";

export default async (req) => {
  const corsHeaders = {
    "Access-Control-Allow-Origin": "https://kleinmed-ag.github.io",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type"
  };

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response("Method Not Allowed", {
      status: 405,
      headers: corsHeaders
    });
  }

  try {
    const payload = await req.json();

    // 1️⃣ Create JWT for GitHub App
    const now = Math.floor(Date.now() / 1000);

    const rawKey = process.env.GITHUB_PRIVATE_KEY;

    // Normalize line breaks (handles all Netlify variants)
    const privateKey = crypto.createPrivateKey({
      key: rawKey.replace(/\\n/g, "\n"),
      format: "pem"
    });

    const now = Math.floor(Date.now() / 1000);

    const appJwt = jwt.sign(
      {
        iat: now - 60,
        exp: now + 600,
        iss: process.env.GITHUB_APP_ID
      }, 
      privateKey,
      { algorithm: "RS256" }
    );


    // 2️⃣ Exchange JWT for installation token
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

    if (!tokenResp.ok) {
      const t = await tokenResp.text();
      return new Response(t, { status: 500, headers: corsHeaders });
    }

    const { token } = await tokenResp.json();

    // 3️⃣ Trigger workflow_dispatch
    const ghResp = await fetch(
      "https://api.github.com/repos/kleinmed-ag/gtin/actions/workflows/generate-udi.yml/dispatches",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          ref: "main",
          inputs: payload
        })
      }
    );

    if (!ghResp.ok) {
      const t = await ghResp.text();
      return new Response(t, { status: ghResp.status, headers: corsHeaders });
    }

    return new Response("OK", {
      status: 200,
      headers: corsHeaders
    });

  } catch (err) {
    return new Response(err.message, {
      status: 500,
      headers: corsHeaders
    });
  }
};
