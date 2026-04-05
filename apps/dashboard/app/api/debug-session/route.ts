import { auth } from "@/lib/auth";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const test = url.searchParams.get("test");

  try {
    if (test === "passkey-list") {
      const result = await auth.api.listPasskeys({ headers: req.headers });
      return Response.json({ ok: true, result });
    }
    if (test === "passkey-register") {
      const result = await auth.api.generatePasskeyRegistrationOptions({ headers: req.headers });
      return Response.json({ ok: true, result });
    }
    const session = await auth.api.getSession({ headers: req.headers });
    return Response.json({ ok: true, hasSession: !!session, userId: session?.user?.id });
  } catch (e: any) {
    return Response.json({
      ok: false,
      error: e?.message,
      code: e?.code,
      stack: e?.stack?.split("\n").slice(0, 8),
    }, { status: 500 });
  }
}
