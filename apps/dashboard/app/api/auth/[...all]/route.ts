let auth: any;
let handler: any;
try {
  const authMod = require("@/lib/auth");
  auth = authMod.auth;
  const { toNextJsHandler } = require("better-auth/next-js");
  handler = toNextJsHandler(auth);
} catch (e: any) {
  console.error("[auth] FATAL: Failed to load auth module:", e?.message);
  console.error(e?.stack?.split("\n").slice(0, 10).join("\n"));
  const errorResponse = () => new Response(
    JSON.stringify({ error: "Auth module failed to load", detail: e?.message }),
    { status: 500, headers: { "Content-Type": "application/json" } }
  );
  handler = { GET: errorResponse, POST: errorResponse };
}

export async function GET(req: Request) {
  try {
    return await handler.GET(req);
  } catch (e: any) {
    console.error("[auth] GET error:", e?.message, e?.stack?.split("\n").slice(0, 5).join("\n"));
    return new Response(JSON.stringify({ error: e?.message || "Internal auth error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}

export async function POST(req: Request) {
  try {
    return await handler.POST(req);
  } catch (e: any) {
    console.error("[auth] POST error:", e?.message, e?.stack?.split("\n").slice(0, 5).join("\n"));
    return new Response(JSON.stringify({ error: e?.message || "Internal auth error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
