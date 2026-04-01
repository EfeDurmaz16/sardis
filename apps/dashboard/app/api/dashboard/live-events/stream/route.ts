import { proxyErrorResponse, sardisProxyResponse } from "@/utils/sardis-proxy"

export async function GET() {
  try {
    const response = await sardisProxyResponse("/api/v2/events/stream", {
      headers: {
        Accept: "text/event-stream",
      },
    })

    if (!response.body) {
      return new Response("Missing upstream event stream body", { status: 502 })
    }

    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
