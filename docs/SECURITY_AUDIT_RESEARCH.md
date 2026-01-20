# Security Audit Research & Engagement

**Date:** January 2026  
**Status:** In Progress  
**Target:** Engage audit firm by Week 2, complete audit by Week 12

---

## Objective

Engage a reputable security audit firm to conduct comprehensive security audits of:
1. **Backend/API:** API endpoints, MPC integration, policy engine
2. **Smart Contracts:** Non-custodial wallet contracts (if used)

**Budget:** $25-50K  
**Timeline:** 4-6 weeks for backend audit, 2-4 weeks for smart contract audit

---

## Audit Scope

### Backend/API Audit

**In Scope:**
- [ ] API endpoints (`sardis-api/`)
- [ ] Core business logic (`sardis-core/`)
- [ ] Chain executor (`sardis-chain/`)
- [ ] Compliance module (`sardis-compliance/`)
- [ ] Authentication and authorization
- [ ] Data storage and encryption
- [ ] Key management (MPC integration)
- [ ] Policy engine
- [ ] Mandate verification (AP2/TAP)

**Out of Scope:**
- Third-party services (Persona, Elliptic, Turnkey, Fireblocks)
- Dashboard frontend (separate audit recommended)
- Development tools (CLI, sandbox)

### Smart Contract Audit

**In Scope:**
- [ ] `SardisAgentWallet.sol` (if used)
- [ ] `SardisEscrow.sol` (if used)
- [ ] `SardisWalletFactory.sol` (if used)
- [ ] Access control
- [ ] Reentrancy protection
- [ ] Integer overflow/underflow
- [ ] Token handling

**Note:** Since we're non-custodial, smart contracts may not be needed. Audit only if contracts are used.

---

## Audit Firm Research

### Target Firms

| Firm | Focus | Location | Contact | Status | Notes |
|------|-------|----------|---------|--------|-------|
| **Trail of Bits** | Smart contracts + Backend | Remote | ⏳ TBD | ⏳ Research | Industry leader |
| **OpenZeppelin** | Smart contracts | Remote | ⏳ TBD | ⏳ Research | Contract-focused |
| **Consensys Diligence** | Smart contracts | Remote | ⏳ TBD | ⏳ Research | Ethereum-focused |
| **Cure53** | Web security | Berlin | ⏳ TBD | ⏳ Research | Web/API expertise |
| **NCC Group** | Full stack | Global | ⏳ TBD | ⏳ Research | Comprehensive |

### Research Criteria
- [ ] Crypto/fintech audit experience
- [ ] MPC integration audit experience
- [ ] API security expertise
- [ ] Smart contract expertise (if needed)
- [ ] Startup-friendly pricing
- [ ] Responsive and available
- [ ] References from similar companies

### Contact Information
- [ ] Research firm websites
- [ ] Find contact information
- [ ] Get referrals from crypto/fintech companies
- [ ] Check LinkedIn for connections

---

## Request for Proposal (RFP)

### RFP Template

**Subject:** Security Audit Request - Agent Payment Infrastructure

**Dear [Audit Firm],**

We are Sardis, a payment infrastructure platform for AI agents. We are seeking a comprehensive security audit of our backend/API and smart contracts.

**Company Overview:**
- **Product:** Non-custodial Agent Wallet & Payment OS
- **Architecture:** FastAPI backend, MPC wallets, multi-chain support
- **Tech Stack:** Python, Solidity, PostgreSQL, Redis
- **Target Market:** AI agents, API providers, agent frameworks

**Scope of Work:**

**Backend/API Audit:**
- API endpoints security
- Authentication and authorization
- MPC integration security
- Policy engine security
- Mandate verification (AP2/TAP)
- Data storage and encryption
- Key management
- Input validation
- Error handling

**Smart Contract Audit (if applicable):**
- Access control
- Reentrancy protection
- Integer overflow/underflow
- Token handling
- State management

**Deliverables:**
- Security audit report
- Vulnerability assessment
- Remediation recommendations
- Follow-up review (if needed)

**Timeline:**
- Proposal due: [Date]
- Engagement start: [Date]
- Audit completion: 4-6 weeks from engagement
- Report delivery: 1 week after completion

**Budget:**
- Target: $25-50K
- Please provide detailed cost breakdown

**Questions:**
Please contact [Your Name] at [Email] or [Phone].

Thank you for your consideration.

---

## Proposal Evaluation

### Evaluation Criteria

| Criterion | Weight | Notes |
|-----------|--------|-------|
| **Expertise** | 30% | Crypto/fintech, MPC, API security |
| **Understanding** | 20% | Do they understand our architecture? |
| **Cost** | 20% | Within budget ($25-50K) |
| **Timeline** | 15% | Can deliver in 4-6 weeks |
| **References** | 10% | Similar companies they've audited |
| **Communication** | 5% | Responsive, clear communication |

### Proposal Tracking

| Firm | Proposal Received | Cost | Timeline | Score | Status |
|------|-------------------|------|----------|-------|--------|
| Trail of Bits | ⏳ TBD | ⏳ TBD | ⏳ TBD | ⏳ TBD | ⏳ Pending |
| OpenZeppelin | ⏳ TBD | ⏳ TBD | ⏳ TBD | ⏳ TBD | ⏳ Pending |
| Consensys Diligence | ⏳ TBD | ⏳ TBD | ⏳ TBD | ⏳ TBD | ⏳ Pending |
| Cure53 | ⏳ TBD | ⏳ TBD | ⏳ TBD | ⏳ TBD | ⏳ Pending |
| NCC Group | ⏳ TBD | ⏳ TBD | ⏳ TBD | ⏳ TBD | ⏳ Pending |

---

## Pre-Audit Preparation

### Documentation Required
- [ ] Architecture diagrams
- [ ] API documentation
- [ ] Data flow diagrams
- [ ] Threat model
- [ ] Known issues list
- [ ] Code access (GitHub repository)
- [ ] Test environment access

### Code Preparation
- [ ] Code is ready for audit (no WIP features)
- [ ] Tests are passing
- [ ] Documentation is up to date
- [ ] Known issues are documented
- [ ] Security checklist completed (see `docs/security-audit-checklist.md`)

### Access Setup
- [ ] GitHub repository access
- [ ] Test environment access
- [ ] API keys for testing
- [ ] Database access (if needed)
- [ ] MPC provider access (if needed)

---

## Engagement Process

### Week 1: Research & Outreach
- [ ] Research 5 audit firms
- [ ] Find contact information
- [ ] Send RFP to 3-5 firms
- [ ] Schedule initial calls

### Week 2: Proposal Review
- [ ] Receive proposals
- [ ] Evaluate proposals
- [ ] Select audit firm
- [ ] Sign engagement letter

### Week 3-4: Preparation
- [ ] Prepare documentation
- [ ] Set up access
- [ ] Complete security checklist
- [ ] Kickoff call with audit team

### Week 5-8: Audit Execution
- [ ] Audit team reviews code
- [ ] Answer questions
- [ ] Provide clarifications
- [ ] Review findings as they come in

### Week 9-10: Report Review
- [ ] Receive draft report
- [ ] Review findings
- [ ] Provide feedback
- [ ] Request clarifications

### Week 11-12: Final Report
- [ ] Receive final report
- [ ] Review and prioritize findings
- [ ] Create remediation plan

---

## Vulnerability Severity

### Critical (P0) - Fix Immediately
- Authentication bypass
- Private key exposure
- Arbitrary code execution
- SQL injection
- Funds theft in contracts

### High (P1) - Fix Within 1 Week
- Authorization bypass
- Sensitive data exposure
- Denial of service
- Reentrancy in contracts

### Medium (P2) - Fix Within 1 Month
- Rate limit bypass
- Information disclosure
- CORS misconfiguration
- Insufficient logging

### Low (P3) - Fix When Possible
- Missing security headers
- Verbose error messages
- Deprecated dependencies

---

## Remediation Plan

### Immediate (Week 1)
- [ ] Address all Critical findings
- [ ] Address all High findings
- [ ] Plan Medium remediations

### Short-term (Week 2-4)
- [ ] Complete Medium remediations
- [ ] Address Low findings
- [ ] Update documentation

### Long-term
- [ ] Schedule follow-up audit
- [ ] Implement continuous scanning
- [ ] Bug bounty program

---

## Budget Tracking

| Item | Estimated Cost | Actual Cost | Notes |
|------|----------------|-------------|-------|
| Backend Audit | $15-30K | ⏳ TBD | Main audit |
| Smart Contract Audit | $10-20K | ⏳ TBD | If contracts used |
| Follow-up Review | $5-10K | ⏳ TBD | If needed |
| **Total** | **$25-50K** | **⏳ TBD** | |

---

## Timeline

| Week | Milestone | Status |
|------|-----------|--------|
| 1 | Research firms, send RFPs | ⏳ In Progress |
| 2 | Receive proposals, select firm | ⏳ Pending |
| 3-4 | Preparation | ⏳ Pending |
| 5-8 | Audit execution | ⏳ Pending |
| 9-10 | Report review | ⏳ Pending |
| 11-12 | Final report | ⏳ Pending |

---

## Next Steps

1. **This Week:**
   - [ ] Research 5 audit firms
   - [ ] Find contact information
   - [ ] Send RFP to 3-5 firms
   - [ ] Schedule initial calls

2. **Next Week:**
   - [ ] Receive proposals
   - [ ] Evaluate proposals
   - [ ] Select audit firm
   - [ ] Sign engagement letter

---

**Last Updated:** January 2026  
**Next Review:** After receiving proposals (Week 2)
