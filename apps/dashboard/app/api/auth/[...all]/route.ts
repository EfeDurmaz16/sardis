import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

const handler = toNextJsHandler(auth);

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
