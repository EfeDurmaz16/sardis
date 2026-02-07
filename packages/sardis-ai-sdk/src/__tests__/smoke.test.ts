import { describe, it, expect } from 'vitest'
import {
  createSardisTools,
  createMinimalSardisTools,
  createReadOnlySardisTools,
  createSardisProvider,
} from '../index'

const baseConfig = {
  apiKey: 'test_key',
  walletId: 'wallet_test_123',
  simulationMode: true,
  maxPaymentAmount: 10,
  blockedCategories: ['adult'],
  allowedMerchants: ['openai'],
}

describe('@sardis/ai-sdk smoke', () => {
  it('creates full toolset with expected tools', () => {
    const tools = createSardisTools(baseConfig)

    expect(tools.sardis_pay).toBeDefined()
    expect(tools.sardis_create_hold).toBeDefined()
    expect(tools.sardis_capture_hold).toBeDefined()
    expect(tools.sardis_void_hold).toBeDefined()
    expect(tools.sardis_check_policy).toBeDefined()
    expect(tools.sardis_get_balance).toBeDefined()
    expect(tools.sardis_get_spending).toBeDefined()
  })

  it('creates minimal and readonly toolsets', () => {
    const minimal = createMinimalSardisTools(baseConfig)
    const readonly = createReadOnlySardisTools(baseConfig)

    expect(Object.keys(minimal)).toEqual(['sardis_pay', 'sardis_get_balance'])
    expect(Object.keys(readonly)).toEqual([
      'sardis_check_policy',
      'sardis_get_balance',
      'sardis_get_spending',
    ])
  })

  it('provider direct pay fails closed on local policy precheck', async () => {
    const provider = createSardisProvider(baseConfig)
    const result = await provider.pay({
      to: '0x1234567890123456789012345678901234567890',
      amount: 99,
      merchant: 'openai',
    })

    expect(result.success).toBe(false)
    expect(result.status).toBe('failed')
    expect(result.error).toContain('exceeds maximum allowed payment')
  })

  it('provider exposes system prompt with payment guidance', () => {
    const provider = createSardisProvider({
      ...baseConfig,
      customInstructions: 'Only allow software spend.',
    })

    expect(provider.systemPrompt).toContain('Payment Guidelines')
    expect(provider.systemPrompt).toContain('Only allow software spend.')
  })
})

