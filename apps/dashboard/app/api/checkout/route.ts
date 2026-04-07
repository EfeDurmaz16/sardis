import { auth } from "@/lib/auth";

const PRODUCTS: Record<string, string> = {
  starter: "7aa8578d-ea9f-4e19-8d5a-377fb3b6e1d9",
  growth: "0f0009fe-fa2f-4052-9af1-ff6fb076055d",
};

export async function POST(req: Request) {
  try {
    const session = await auth.api.getSession({ headers: req.headers });
    if (!session) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    const { plan } = await req.json();
    const productId = PRODUCTS[plan];
    if (!productId) {
      return Response.json({ error: "Invalid plan" }, { status: 400 });
    }

    const token = process.env.POLAR_ACCESS_TOKEN;
    if (!token) {
      return Response.json({ error: "Billing not configured" }, { status: 503 });
    }

    const res = await fetch("https://api.polar.sh/v1/checkouts/", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        product_id: productId,
        success_url: "https://app.sardis.sh/billing?success=1",
        metadata: {
          user_id: session.user.id,
          email: session.user.email,
          plan,
        },
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error("[checkout] Polar API error:", res.status, err);
      return Response.json({ error: "Checkout creation failed" }, { status: 502 });
    }

    const data = await res.json();
    return Response.json({ url: data.url });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown checkout error";
    console.error("[checkout] Error:", message);
    return Response.json({ error: message }, { status: 500 });
  }
}
