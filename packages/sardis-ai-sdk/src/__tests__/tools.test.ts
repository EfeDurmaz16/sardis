import { describe, it, expect } from 'vitest'
import { createSardisTools, createMinimalSardisTools, createReadOnlySardisTools } from '../tools'
import { SardisProvider } from '../provider'

const baseConfig = {
  apiKey: 'test_api_key',
  walletId: 'wallet_test_123',
  simulationMode: true,
}

describe('sardis ai sdk tools', () => {
  it('creates full toolset with expected keys', () => {
    const tools = createSardisTools(baseConfig)

    expect(Object.keys(tools)).toEqual(
      expect.arrayContaining([
        'sardis_pay',
        'sardis_create_hold',
        'sardis_capture_hold',
        'sardis_void_hold',
        'sardis_check_policy',
        'sardis_get_balance',
        'sardis_get_spending',
      ])
    )
  })

  it('blocks payment via local policy pre-check', async () => {
    const tools = createSardisTools({
      ...baseConfig,
      maxPaymentAmount: 25,
    })

    const result = await tools.sardis_pay.execute(
      {
        to: '0xabc',
        amount: 30,
        merchant: 'OpenAI',
      },
      { toolCallId: 'tool_call_1', messages: [] }
    )

    expect(result.success).toBe(false)
    expect(result.status).toBe('failed')
    expect(result.error).toContain('exceeds maximum allowed payment')
  })

  it('creates minimal and read-only toolsets', () => {
    const minimal = createMinimalSardisTools(baseConfig)
    expect(Object.keys(minimal)).toEqual(['sardis_pay', 'sardis_get_balance'])

    const readonly = createReadOnlySardisTools(baseConfig)
    expect(Object.keys(readonly)).toEqual([
      'sardis_check_policy',
      'sardis_get_balance',
      'sardis_get_spending',
    ])
  })

  it('provider exposes tools and system prompt', () => {
    const provider = new SardisProvider({
      ...baseConfig,
      toolSet: 'minimal',
      customInstructions: 'Only pay for approved SaaS vendors.',
    })

    expect(Object.keys(provider.tools)).toEqual(['sardis_pay', 'sardis_get_balance'])
    expect(provider.systemPrompt).toContain('Only pay for approved SaaS vendors.')
  })
})
