import { NextResponse } from "next/server"

import { proxyErrorResponse, sardisProxyFetch } from "@/utils/sardis-proxy"

type RemoteAgent = {
  agent_id: string
  name?: string
  wallet_id?: string | null
}

type SimulationRequest = {
  amount: string
  currency: string
  chain: string
  sender_agent_id: string
  source: string
  recipient_address: string
}

export async function GET() {
  try {
    const agents = await sardisProxyFetch<RemoteAgent[]>("/api/v2/agents")
    return NextResponse.json({
      agents: agents.map((agent) => ({
        agentId: agent.agent_id,
        name: agent.name || agent.agent_id,
        walletId: agent.wallet_id || null,
      })),
    })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as SimulationRequest
    const response = await sardisProxyFetch("/api/v2/simulate", {
      method: "POST",
      body: JSON.stringify(body),
    })
    return NextResponse.json(response)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
