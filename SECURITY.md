# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously at Sardis. If you discover a security vulnerability, please report it responsibly.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please report vulnerabilities via one of these channels:

1. **GitHub Security Advisories** (preferred): Use [GitHub's private vulnerability reporting](https://github.com/EfeDurmaz16/sardis/security/advisories/new)
2. **Email**: Send details to **security@sardis.sh**

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 5 business days
- **Resolution Target**: Within 30 days for critical issues, 90 days for others

### Scope

The following are in scope for security reports:

- Sardis API (`packages/sardis-api`)
- Sardis Core (`packages/sardis-core`)
- Smart Contracts (`contracts/`)
- Wallet Management (`packages/sardis-wallet`)
- Chain Execution (`packages/sardis-chain`)
- SDKs (`packages/sardis-sdk-python`, `packages/sardis-sdk-js`, `sardis/`)
- MCP Server (`packages/sardis-mcp-server`)

### Out of Scope

- Third-party services (Turnkey, Persona, Elliptic, Lithic)
- Marketing website content
- Demo applications

### Disclosure Policy

- We follow coordinated disclosure practices
- Credit will be given to reporters (unless anonymity is requested)
- We will not pursue legal action against researchers acting in good faith

## Security Practices

- Non-custodial MPC wallet architecture (no private key storage)
- All transactions pass policy checks before execution
- Append-only audit ledger for all operations
- API keys hashed with SHA-256
- HMAC webhook signature verification
- Rate limiting on all endpoints
- Automated dependency scanning via Dependabot
- Static analysis via Bandit (Python) and Trivy (containers)
- OpenSSF Scorecard monitoring
