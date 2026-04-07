import { toNextJsHandler } from "better-auth/next-js";

type BetterAuthHandler = ReturnType<typeof toNextJsHandler>;

let handler: BetterAuthHandler;
let initError: string | null = null;

function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  return "Unknown error";
}

try {
  // Dynamic import to catch any module-level errors
  const { auth } = await import("@/lib/auth");
  handler = toNextJsHandler(auth);
} catch (e: unknown) {
  initError = errorMessage(e) || "Unknown auth init error";
  console.error("[auth] INIT FAILED:", initError, e instanceof Error ? e.stack : undefined);
  // Fallback handler that returns the error for both GET and POST
  const errResponse = async () => Response.json({ error: initError }, { status: 500 });
  handler = { GET: errResponse, POST: errResponse } satisfies BetterAuthHandler;
}

export async function GET(req: Request) {
  if (initError) return Response.json({ error: initError }, { status: 500 });
  try {
    return await handler.GET(req);
  } catch (e: unknown) {
    const message = errorMessage(e);
    console.error("[auth] GET error:", message);
    return Response.json({ error: message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  if (initError) return Response.json({ error: initError }, { status: 500 });
  try {
    return await handler.POST(req);
  } catch (e: unknown) {
    const message = errorMessage(e);
    console.error("[auth] POST error:", message);
    return Response.json({ error: message }, { status: 500 });
  }
}
