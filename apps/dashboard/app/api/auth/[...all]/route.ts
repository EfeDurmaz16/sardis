import { toNextJsHandler } from "better-auth/next-js";

let handler: ReturnType<typeof toNextJsHandler>;
let initError: string | null = null;

try {
  // Dynamic import to catch any module-level errors
  const { auth } = await import("@/lib/auth");
  handler = toNextJsHandler(auth);
} catch (e: any) {
  initError = e?.message || "Unknown auth init error";
  console.error("[auth] INIT FAILED:", initError, e?.stack);
  // Fallback handler that returns the error
  const errResponse = () => Response.json({ error: initError }, { status: 500 });
  handler = { GET: errResponse, POST: errResponse } as any;
}

export async function GET(req: Request) {
  if (initError) return Response.json({ error: initError }, { status: 500 });
  try {
    return await handler.GET(req);
  } catch (e: any) {
    console.error("[auth] GET error:", e?.message);
    return Response.json({ error: e?.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  if (initError) return Response.json({ error: initError }, { status: 500 });
  try {
    return await handler.POST(req);
  } catch (e: any) {
    console.error("[auth] POST error:", e?.message);
    return Response.json({ error: e?.message }, { status: 500 });
  }
}
