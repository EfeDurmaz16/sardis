import { auth } from "@/lib/auth";

export async function GET(req: Request) {
  try {
    const session = await auth.api.getSession({ headers: req.headers });
    return Response.json({ ok: true, hasSession: !!session });
  } catch (e: any) {
    return Response.json({
      ok: false,
      error: e?.message,
      name: e?.name,
      code: e?.code,
      stack: e?.stack?.split("\n").slice(0, 8),
    }, { status: 500 });
  }
}
