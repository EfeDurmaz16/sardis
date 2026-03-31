import { NextResponse } from "next/server"

import { proxyErrorResponse, sardisProxyFetch } from "@/utils/sardis-proxy"

type RemoteReceiveAddress = {
  chain: string
  address: string
  eip681_uri: string
  token: string
}

type RemoteReceiveInfo = {
  wallet_id: string
  addresses: RemoteReceiveAddress[]
}

export async function GET(_: Request, context: { params: Promise<{ walletId: string }> }) {
  try {
    const { walletId } = await context.params
    const response = await sardisProxyFetch<RemoteReceiveInfo>(`/api/v2/wallets/${walletId}/receive`)
    return NextResponse.json(response)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
