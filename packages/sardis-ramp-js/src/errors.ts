/**
 * Custom error classes for Sardis Fiat Ramp.
 */

export class PolicyViolation extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PolicyViolation'
  }
}

export class RampError extends Error {
  public code: string
  public details?: Record<string, unknown>

  constructor(message: string, code: string, details?: Record<string, unknown>) {
    super(message)
    this.name = 'RampError'
    this.code = code
    this.details = details
  }
}
