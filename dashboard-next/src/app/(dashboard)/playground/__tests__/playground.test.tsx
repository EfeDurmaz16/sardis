import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PlaygroundPage from '../page'

// Mock fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ success: true, tx_id: 'tx_test_001' }),
  } as Response)
)

describe('PlaygroundPage', () => {
  it('renders the page header', () => {
    render(<PlaygroundPage />)
    expect(screen.getByText('API Playground')).toBeDefined()
  })

  it('renders endpoint picker with all endpoints', () => {
    render(<PlaygroundPage />)
    expect(screen.getByText('sardis.pay()')).toBeDefined()
    expect(screen.getByText('/policy/check')).toBeDefined()
    expect(screen.getByText('/wallets/create')).toBeDefined()
    expect(screen.getByText('/sandbox/demo-data')).toBeDefined()
  })

  it('renders the Run Request button', () => {
    render(<PlaygroundPage />)
    const buttons = screen.getAllByText('Run Request')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('switches endpoint when clicked', () => {
    render(<PlaygroundPage />)
    const policyBtn = screen.getByText('/policy/check')
    fireEvent.click(policyBtn)
    expect(screen.getByText("Dry-run a payment against an agent's spending policy")).toBeDefined()
  })

  it('shows execution trace empty state', () => {
    render(<PlaygroundPage />)
    expect(screen.getByText(/Run Request.*to see the execution trace/)).toBeDefined()
  })

  it('shows result inspector empty state', () => {
    render(<PlaygroundPage />)
    expect(screen.getByText('Run a request to see the response')).toBeDefined()
  })
})
