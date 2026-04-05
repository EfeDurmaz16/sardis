export function GET() {
  const plugin = {
    schema_version: "v1",
    name_for_human: "Sardis Payments",
    name_for_model: "sardis",
    description_for_human:
      "AI agent payment infrastructure with policy-controlled wallets",
    description_for_model:
      "Use Sardis to create wallets, execute payments, manage spending policies, and issue virtual cards for AI agents. Supports USDC stablecoin payments on Base, Polygon, Ethereum, Arbitrum, Optimism. All transactions enforce natural language spending policies.",
    auth: {
      type: "service_http",
      authorization_type: "bearer",
    },
    api: {
      type: "openapi",
      url: "https://api.sardis.sh/api/v2/openapi.json",
    },
    logo_url: "https://sardis.sh/icon.svg",
    contact_email: "contact@sardis.sh",
    legal_info_url: "https://sardis.sh/legal",
  };

  return new Response(JSON.stringify(plugin, null, 2), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
