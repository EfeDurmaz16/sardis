import { NextResponse } from "next/server"

import { proxyErrorResponse, sardisProxyFetch, sardisProxyListFetch } from "@/utils/sardis-proxy"

type RemoteWallet = {
  wallet_id: string
  agent_id: string
  mpc_provider: string
  account_type: string
  addresses: Record<string, string>
  currency: string
  limit_per_tx: string
  limit_total: string
  is_active: boolean
  created_at: string
  updated_at: string
}

type RemoteAgent = {
  agent_id: string
  name?: string
}

type RemoteBalanceEntry = {
  chain: string
  token: string
  balance: string
  address: string
}

type RemoteMultiChainBalance = {
  wallet_id: string
  total_usd: string
  total_eur: string
  balances: RemoteBalanceEntry[]
  queried_at: string
}

type RemoteDeposit = {
  deposit_id: string
  tx_hash: string
  chain: string
  token: string
  from_address: string
  to_address: string
  amount: string
  status: string
  confirmed_at: string | null
  detected_at: string | null
  credited_at: string | null
}

type WalletSnapshot = {
  walletId: string
  agentId: string
  name: string
  primaryAddress: string | null
  primaryChain: string | null
  currency: string
  provider: string
  accountType: string
  isActive: boolean
  totalUsd: string | null
  totalEur: string | null
  limitPerTx: string
  limitTotal: string
  balances: RemoteBalanceEntry[]
  pendingDeposits: number
  pendingAmountUsd: string
  lastActivityAt: string | null
  createdAt: string
  updatedAt: string
}

type DepositSummary = {
  walletId: string
  walletName: string
  depositId: string
  amount: string
  chain: string
  status: string
  detectedAt: string | null
  txHash: string
}

function parseDecimal(value: string | null | undefined): number {
  if (!value) return 0
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function formatDecimal(value: number): string {
  return value.toFixed(2)
}

function derivePrimaryAddress(addresses: Record<string, string>) {
  for (const [chain, address] of Object.entries(addresses || {})) {
    if (address) {
      return { chain, address }
    }
  }
  return { chain: null, address: null }
}

async function fetchOptional<T>(path: string): Promise<T | null> {
  try {
    return await sardisProxyFetch<T>(path)
  } catch {
    return null
  }
}

async function fetchOptionalList<T>(path: string): Promise<T[]> {
  try {
    return await sardisProxyListFetch<T>(path)
  } catch {
    return []
  }
}

export async function GET() {
  try {
    const [wallets, agents] = await Promise.all([
      sardisProxyListFetch<RemoteWallet>("/api/v2/wallets"),
      fetchOptionalList<RemoteAgent>("/api/v2/agents"),
    ])

    const agentNameById = new Map((agents || []).map((agent) => [agent.agent_id, agent.name || agent.agent_id]))

    const walletSnapshots = await Promise.all(
      wallets.map(async (wallet): Promise<WalletSnapshot> => {
        const [balances, deposits] = await Promise.all([
          fetchOptional<RemoteMultiChainBalance>(`/api/v2/wallets/${wallet.wallet_id}/balances`),
          fetchOptionalList<RemoteDeposit>(`/api/v2/wallets/${wallet.wallet_id}/deposits?limit=5`),
        ])

        const { chain, address } = derivePrimaryAddress(wallet.addresses)
        const depositList = deposits
        const pendingDeposits = depositList.filter((deposit) => deposit.status !== "credited").length
        const pendingAmountUsd = depositList
          .filter((deposit) => deposit.status !== "credited")
          .reduce((sum, deposit) => sum + parseDecimal(deposit.amount), 0)

        const lastActivityAt = depositList
          .map((deposit) => deposit.credited_at || deposit.confirmed_at || deposit.detected_at)
          .filter((value): value is string => Boolean(value))
          .sort((left, right) => new Date(right).getTime() - new Date(left).getTime())[0] ?? null

        return {
          walletId: wallet.wallet_id,
          agentId: wallet.agent_id,
          name: agentNameById.get(wallet.agent_id) || wallet.wallet_id,
          primaryAddress: address,
          primaryChain: chain,
          currency: wallet.currency,
          provider: wallet.mpc_provider,
          accountType: wallet.account_type,
          isActive: wallet.is_active,
          totalUsd: balances?.total_usd ?? null,
          totalEur: balances?.total_eur ?? null,
          limitPerTx: wallet.limit_per_tx,
          limitTotal: wallet.limit_total,
          balances: balances?.balances ?? [],
          pendingDeposits,
          pendingAmountUsd: formatDecimal(pendingAmountUsd),
          lastActivityAt,
          createdAt: wallet.created_at,
          updatedAt: wallet.updated_at,
        }
      }),
    )

    const chainTotals = new Map<string, number>()
    const recentDeposits: DepositSummary[] = []

    walletSnapshots.forEach((wallet) => {
      wallet.balances.forEach((balance) => {
        if (balance.token !== "USDC") return
        chainTotals.set(balance.chain, (chainTotals.get(balance.chain) || 0) + parseDecimal(balance.balance))
      })
    })

    await Promise.all(
      walletSnapshots.map(async (wallet) => {
        const deposits = await fetchOptionalList<RemoteDeposit>(`/api/v2/wallets/${wallet.walletId}/deposits?limit=3`)
        deposits.forEach((deposit) => {
          recentDeposits.push({
            walletId: wallet.walletId,
            walletName: wallet.name,
            depositId: deposit.deposit_id,
            amount: deposit.amount,
            chain: deposit.chain,
            status: deposit.status,
            detectedAt: deposit.detected_at || deposit.confirmed_at || deposit.credited_at,
            txHash: deposit.tx_hash,
          })
        })
      }),
    )

    const totalUsd = walletSnapshots.reduce((sum, wallet) => sum + parseDecimal(wallet.totalUsd), 0)
    const walletCount = walletSnapshots.length
    const pendingDeposits = walletSnapshots.reduce((sum, wallet) => sum + wallet.pendingDeposits, 0)

    return NextResponse.json({
      wallets: walletSnapshots,
      totals: {
        totalUsd: formatDecimal(totalUsd),
        walletCount,
        averageBalanceUsd: formatDecimal(walletCount > 0 ? totalUsd / walletCount : 0),
        pendingDeposits,
      },
      chainBalances: Array.from(chainTotals.entries())
        .map(([chain, amount]) => ({ chain, amount: formatDecimal(amount) }))
        .sort((left, right) => parseDecimal(right.amount) - parseDecimal(left.amount)),
      recentDeposits: recentDeposits
        .sort((left, right) => new Date(right.detectedAt || 0).getTime() - new Date(left.detectedAt || 0).getTime())
        .slice(0, 10),
    })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
