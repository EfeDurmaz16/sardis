# sardis-compliance

[![PyPI version](https://badge.fury.io/py/sardis-compliance.svg)](https://badge.fury.io/py/sardis-compliance)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Compliance and monitoring services for Sardis - KYC, Sanctions, PEP, Risk Scoring, and Reporting.

## Overview

`sardis-compliance` provides comprehensive compliance infrastructure aligned with the U.S. GENIUS Act:

- **KYC Verification**: Identity verification with Persona integration
- **Sanctions Screening**: OFAC/SDN screening via Elliptic
- **PEP Screening**: Politically Exposed Persons checks
- **Risk Scoring**: Real-time transaction risk assessment
- **Adverse Media**: News and media monitoring
- **Compliance Reporting**: Automated report generation
- **Audit Trail**: Immutable compliance audit logs

## Installation

```bash
pip install sardis-compliance
```

### Optional Dependencies

```bash
# PostgreSQL support
pip install sardis-compliance[postgres]

# S3 archive storage
pip install sardis-compliance[s3]

# Google Cloud Storage
pip install sardis-compliance[gcs]

# PDF report generation
pip install sardis-compliance[pdf]

# All optional dependencies
pip install sardis-compliance[all]
```

## Quick Start

```python
from sardis_compliance import (
    ComplianceEngine,
    create_kyc_service,
    create_sanctions_service,
    create_risk_scorer,
)

# Initialize services
kyc = create_kyc_service(provider="persona")
sanctions = create_sanctions_service(provider="elliptic")
risk_scorer = create_risk_scorer()

# Run compliance checks
engine = ComplianceEngine(
    kyc_service=kyc,
    sanctions_service=sanctions,
    risk_scorer=risk_scorer,
)

result = await engine.check_transaction(
    wallet_address="0x...",
    amount=10000_00,  # $10,000
    counterparty="0x...",
)

if result.approved:
    print("Transaction approved")
else:
    print(f"Blocked: {result.reason}")
```

## Features

### KYC Verification

```python
from sardis_compliance import create_kyc_service, VerificationRequest

kyc = create_kyc_service(provider="persona")

# Create verification session
session = await kyc.create_session(
    request=VerificationRequest(
        user_id="user_123",
        email="user@example.com",
        verification_level="enhanced",
    )
)

# Check verification status
result = await kyc.check_status(session.inquiry_id)
print(f"Status: {result.status}")
print(f"Verified: {result.verified}")
```

### Sanctions Screening

```python
from sardis_compliance import create_sanctions_service

sanctions = create_sanctions_service(provider="elliptic")

# Screen a wallet address
result = await sanctions.screen_wallet(
    address="0x...",
    chain="ethereum",
)

if result.risk == "HIGH":
    print(f"High risk! Matched lists: {result.matched_lists}")
```

### PEP Screening

```python
from sardis_compliance import create_pep_service, PEPScreeningRequest

pep = create_pep_service(provider="complyadvantage")

result = await pep.screen(
    request=PEPScreeningRequest(
        full_name="John Smith",
        date_of_birth="1970-01-15",
        nationality="US",
    )
)

for match in result.matches:
    print(f"Match: {match.name} - {match.category}")
```

### Risk Scoring

```python
from sardis_compliance import create_risk_scorer

scorer = create_risk_scorer()

assessment = await scorer.assess_transaction(
    wallet_id="wal_123",
    amount=50000_00,
    counterparty="0x...",
    transaction_type="outbound",
)

print(f"Risk Level: {assessment.level}")
print(f"Risk Score: {assessment.score}")
print(f"Factors: {assessment.factors}")
print(f"Action: {assessment.recommended_action}")
```

### Compliance Reporting

```python
from sardis_compliance import create_report_service, ReportType

reports = create_report_service()

# Generate a compliance report
report = await reports.generate(
    report_type=ReportType.MONTHLY_SUMMARY,
    start_date=start,
    end_date=end,
    format="pdf",
)

await reports.save(report, path="/reports/monthly.pdf")
```

### Audit Trail

```python
from sardis_compliance import get_audit_store

audit = get_audit_store()

# Log a compliance decision
await audit.log(
    action="TRANSACTION_APPROVED",
    wallet_id="wal_123",
    decision="approved",
    risk_score=25,
    checks_performed=["kyc", "sanctions", "pep"],
)

# Query audit history
entries = await audit.query(
    wallet_id="wal_123",
    start_date=start,
    end_date=end,
)
```

## Configuration

```bash
# KYC Provider (Persona)
SARDIS_PERSONA_API_KEY=your-api-key
SARDIS_PERSONA_TEMPLATE_ID=tmpl_xxx

# Sanctions Provider (Elliptic)
SARDIS_ELLIPTIC_API_KEY=your-api-key
SARDIS_ELLIPTIC_API_SECRET=your-secret

# PEP Provider (ComplyAdvantage)
SARDIS_COMPLYADVANTAGE_API_KEY=your-api-key

# Risk Scoring
SARDIS_RISK_HIGH_THRESHOLD=75
SARDIS_RISK_MEDIUM_THRESHOLD=50
```

## Architecture

```
sardis-compliance/
├── checks.py         # Compliance engine
├── kyc.py            # KYC verification
├── sanctions.py      # Sanctions screening
├── pep.py            # PEP screening
├── risk_scoring.py   # Risk assessment
├── adverse_media.py  # Media monitoring
├── reports.py        # Report generation
├── dashboard.py      # Compliance dashboard
├── batch.py          # Batch processing
├── audit_rotation.py # Audit log management
└── retry.py          # Resilience utilities
```

## Requirements

- Python 3.11+
- sardis-core >= 0.1.0
- httpx >= 0.25.0

## Documentation

Full documentation is available at [docs.sardis.sh/compliance](https://docs.sardis.sh/compliance).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.
