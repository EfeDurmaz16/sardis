# Compliance Framework

## Overview

This document outlines Sardis's compliance framework for operating a stablecoin payment network for AI agents. It covers regulatory considerations, KYC/AML integration, geographic restrictions, and audit requirements.

## Regulatory Landscape

### Key Regulations

| Region | Regulation | Applicability |
|--------|------------|---------------|
| USA | FinCEN MSB | Money transmission |
| USA | State MTL | Per-state licensing |
| EU | MiCA | Crypto-asset service |
| EU | PSD2 | Payment services |
| UK | FCA | E-money/payment |
| Singapore | MAS PS Act | Payment services |
| Global | FATF Guidelines | AML/CFT standards |

### Sardis Classification

Sardis operates as a **payment infrastructure provider** that:
1. Facilitates stablecoin transfers between AI agents
2. Does not take custody of user funds (MPC model)
3. Provides programmable spending controls
4. Maintains transaction records

**Regulatory Strategy:**
- Partner with licensed entities where required
- Implement compliance-as-a-service integrations
- Maintain flexibility for jurisdiction-specific requirements

## KYC Integration

### Tiered KYC Model

```
┌─────────────────────────────────────────────────────────────┐
│                     KYC TIERS                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  TIER 1: Basic (No KYC)                                     │
│  ├── Daily limit: $500                                      │
│  ├── Monthly limit: $2,000                                  │
│  ├── Requirements: Email only                               │
│  └── Use case: Testing, small transactions                  │
│                                                              │
│  TIER 2: Standard KYC                                       │
│  ├── Daily limit: $10,000                                   │
│  ├── Monthly limit: $50,000                                 │
│  ├── Requirements:                                          │
│  │   ├── Full name                                          │
│  │   ├── Date of birth                                      │
│  │   ├── Address                                            │
│  │   └── Government ID                                      │
│  └── Use case: Individual developers                        │
│                                                              │
│  TIER 3: Enhanced KYC (Business)                            │
│  ├── Daily limit: $100,000                                  │
│  ├── Monthly limit: Unlimited                               │
│  ├── Requirements:                                          │
│  │   ├── Company registration                               │
│  │   ├── Beneficial ownership                               │
│  │   ├── Source of funds                                    │
│  │   └── Business documentation                             │
│  └── Use case: Enterprise, high-volume                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### KYC Provider Integration

```python
from abc import ABC, abstractmethod

class KYCProvider(ABC):
    """Abstract KYC provider interface."""
    
    @abstractmethod
    async def verify_individual(
        self,
        full_name: str,
        date_of_birth: str,
        address: dict,
        document: bytes,
        document_type: str
    ) -> KYCResult:
        pass
    
    @abstractmethod
    async def verify_business(
        self,
        company_name: str,
        registration_number: str,
        jurisdiction: str,
        beneficial_owners: list[dict]
    ) -> KYCResult:
        pass


class JumioProvider(KYCProvider):
    """Jumio KYC integration."""
    
    async def verify_individual(self, **kwargs) -> KYCResult:
        # Create Jumio transaction
        response = await self.client.post(
            "/api/v1/accounts",
            json={
                "customerInternalReference": kwargs["user_id"],
                "workflowDefinition": {
                    "key": "ID_VERIFICATION"
                }
            }
        )
        
        return KYCResult(
            transaction_id=response["transactionReference"],
            status="pending",
            redirect_url=response["redirectUrl"]
        )


class SumsubProvider(KYCProvider):
    """Sumsub KYC integration."""
    
    async def verify_individual(self, **kwargs) -> KYCResult:
        # Similar implementation for Sumsub
        pass
```

### KYC Workflow

```
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│  User  │    │ Sardis │    │  KYC   │    │ Review │    │Database│
│        │    │  API   │    │Provider│    │ Queue  │    │        │
└───┬────┘    └───┬────┘    └───┬────┘    └───┬────┘    └───┬────┘
    │             │             │             │             │
    │ Start KYC   │             │             │             │
    │────────────>│             │             │             │
    │             │ Create      │             │             │
    │             │────────────>│             │             │
    │             │<────────────│             │             │
    │<────────────│ Redirect URL│             │             │
    │             │             │             │             │
    │ Submit docs │             │             │             │
    │─────────────────────────>│             │             │
    │             │             │             │             │
    │             │ Webhook:    │             │             │
    │             │ Verified    │             │             │
    │             │<────────────│             │             │
    │             │             │             │             │
    │             │ If manual review needed:  │             │
    │             │────────────────────────────>│            │
    │             │                            │             │
    │             │ Update KYC status          │             │
    │             │─────────────────────────────────────────>│
    │             │                                          │
    │<────────────│ Verified                                 │
```

## AML Monitoring

### Transaction Monitoring

```python
class AMLMonitor:
    """Real-time transaction monitoring for AML."""
    
    # Suspicious activity thresholds
    THRESHOLDS = {
        "structuring": {
            "count": 5,
            "window_hours": 24,
            "amount_below": Decimal("9000")  # Just under $10K
        },
        "velocity": {
            "count": 20,
            "window_hours": 1
        },
        "large_transaction": {
            "amount": Decimal("10000")
        },
        "round_amounts": {
            "count": 3,
            "window_hours": 24
        }
    }
    
    async def screen_transaction(
        self,
        tx: Transaction,
        agent_history: list[Transaction]
    ) -> AMLScreeningResult:
        """Screen a transaction for suspicious activity."""
        
        alerts = []
        
        # Check for structuring
        if self._check_structuring(tx, agent_history):
            alerts.append(AMLAlert(
                type="STRUCTURING",
                severity="HIGH",
                description="Possible structuring to avoid reporting"
            ))
        
        # Check velocity
        if self._check_velocity(agent_history):
            alerts.append(AMLAlert(
                type="HIGH_VELOCITY",
                severity="MEDIUM",
                description="Unusual transaction velocity"
            ))
        
        # Check against sanctions lists
        sanctions_hit = await self._check_sanctions(tx)
        if sanctions_hit:
            alerts.append(AMLAlert(
                type="SANCTIONS",
                severity="CRITICAL",
                description=f"Address matches sanctions list: {sanctions_hit}"
            ))
        
        return AMLScreeningResult(
            transaction_id=tx.tx_id,
            passed=len(alerts) == 0,
            alerts=alerts,
            risk_score=self._calculate_risk_score(alerts)
        )
    
    def _check_structuring(
        self,
        tx: Transaction,
        history: list[Transaction]
    ) -> bool:
        """Check for transaction structuring."""
        threshold = self.THRESHOLDS["structuring"]
        window = timedelta(hours=threshold["window_hours"])
        
        recent = [
            t for t in history
            if t.created_at > datetime.now(timezone.utc) - window
            and t.amount < threshold["amount_below"]
        ]
        
        return len(recent) >= threshold["count"]
```

### Sanctions Screening

```python
class SanctionsScreener:
    """Screen addresses against sanctions lists."""
    
    # Sanctions data providers
    PROVIDERS = ["chainalysis", "elliptic", "trm"]
    
    async def screen_address(self, address: str, chain: str) -> SanctionsResult:
        """Screen an address against sanctions lists."""
        
        # Check OFAC SDN list
        ofac_result = await self._check_ofac(address)
        if ofac_result.match:
            return SanctionsResult(
                flagged=True,
                source="OFAC",
                entity=ofac_result.entity
            )
        
        # Check blockchain analytics providers
        for provider in self.PROVIDERS:
            result = await self._check_provider(provider, address, chain)
            if result.risk_score > 0.8:  # High risk
                return SanctionsResult(
                    flagged=True,
                    source=provider,
                    risk_score=result.risk_score,
                    categories=result.categories
                )
        
        return SanctionsResult(flagged=False)
    
    async def _check_ofac(self, address: str) -> OFACResult:
        """Check against OFAC SDN list."""
        # Use OFAC API or local database
        pass
```

### Suspicious Activity Reports (SAR)

```python
class SARGenerator:
    """Generate Suspicious Activity Reports."""
    
    async def generate_sar(
        self,
        alerts: list[AMLAlert],
        agent: Agent,
        transactions: list[Transaction]
    ) -> SARReport:
        """Generate a SAR for regulatory filing."""
        
        return SARReport(
            report_id=f"SAR_{uuid.uuid4().hex[:16]}",
            filing_date=datetime.now(timezone.utc),
            subject={
                "type": "AI_AGENT",
                "identifier": agent.agent_id,
                "owner": agent.owner_id,
            },
            suspicious_activity={
                "type": alerts[0].type,
                "description": self._generate_narrative(alerts, transactions),
                "date_range": self._get_date_range(transactions),
                "amount_involved": sum(t.amount for t in transactions),
            },
            supporting_transactions=[
                {
                    "tx_id": t.tx_id,
                    "date": t.created_at,
                    "amount": t.amount,
                    "currency": t.currency,
                }
                for t in transactions
            ]
        )
```

## Geographic Restrictions

### Restricted Jurisdictions

```python
class GeoRestrictions:
    """Manage geographic restrictions."""
    
    # OFAC sanctioned countries
    BLOCKED_COUNTRIES = {
        "CU",  # Cuba
        "IR",  # Iran
        "KP",  # North Korea
        "SY",  # Syria
        "RU",  # Russia (partial)
    }
    
    # Countries requiring enhanced due diligence
    HIGH_RISK_COUNTRIES = {
        "AF",  # Afghanistan
        "BY",  # Belarus
        "MM",  # Myanmar
        "VE",  # Venezuela
        "YE",  # Yemen
    }
    
    # US states with specific requirements
    US_RESTRICTED_STATES = {
        "NY",  # BitLicense required
        "HI",  # Not licensed
        "WA",  # Specific requirements
    }
    
    async def check_jurisdiction(
        self,
        ip_address: str,
        declared_country: str
    ) -> JurisdictionResult:
        """Check if jurisdiction is allowed."""
        
        # Geo-locate IP
        geo = await self._geolocate(ip_address)
        
        # Check for VPN/proxy
        if geo.is_vpn or geo.is_proxy:
            return JurisdictionResult(
                allowed=False,
                reason="VPN/Proxy detected"
            )
        
        # Check against blocked list
        country = geo.country_code
        if country in self.BLOCKED_COUNTRIES:
            return JurisdictionResult(
                allowed=False,
                reason=f"Country {country} is restricted"
            )
        
        # Check for mismatch
        if country != declared_country:
            return JurisdictionResult(
                allowed=True,
                warning="Location mismatch detected",
                requires_review=True
            )
        
        return JurisdictionResult(allowed=True)
```

### IP Geolocation

```python
class GeoLocationService:
    """IP geolocation and VPN detection."""
    
    async def geolocate(self, ip: str) -> GeoResult:
        """Get geographic information for an IP."""
        
        # Use MaxMind GeoIP2
        response = await self.maxmind.city(ip)
        
        # Check against VPN database
        is_vpn = await self._check_vpn(ip)
        
        return GeoResult(
            ip=ip,
            country_code=response.country.iso_code,
            country_name=response.country.name,
            region=response.subdivisions.most_specific.name,
            city=response.city.name,
            is_vpn=is_vpn,
            is_proxy=response.traits.is_anonymous_proxy,
            is_datacenter=self._is_datacenter(response.traits.isp)
        )
```

## Audit Trail

### Transaction Logging

```python
class AuditLogger:
    """Immutable audit logging for compliance."""
    
    async def log_transaction(self, tx: Transaction, context: dict):
        """Log a transaction with full context."""
        
        audit_entry = AuditEntry(
            entry_id=f"audit_{uuid.uuid4().hex}",
            timestamp=datetime.now(timezone.utc),
            event_type="TRANSACTION",
            
            # Transaction details
            transaction_id=tx.tx_id,
            from_wallet=tx.from_wallet,
            to_wallet=tx.to_wallet,
            amount=tx.amount,
            currency=tx.currency,
            
            # Context
            agent_id=context["agent_id"],
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            geo_location=context.get("geo_location"),
            
            # Risk data
            risk_score=context.get("risk_score"),
            aml_screening=context.get("aml_result"),
            
            # Signature for integrity
            signature=self._sign_entry(audit_entry)
        )
        
        # Store in append-only log
        await self._store_immutable(audit_entry)
        
        # Replicate to compliance partner
        await self._replicate_to_partner(audit_entry)
```

### Retention Policy

| Data Type | Retention Period | Storage |
|-----------|------------------|---------|
| Transaction records | 7 years | Cold storage |
| KYC documents | 5 years post-relationship | Encrypted S3 |
| AML alerts | 7 years | Compliance database |
| SAR filings | Indefinite | Secure archive |
| Audit logs | 7 years | Append-only log |
| IP/Session logs | 2 years | Log analytics |

### Data Export

```python
class ComplianceExporter:
    """Export data for regulatory requests."""
    
    async def export_agent_data(
        self,
        agent_id: str,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> ExportResult:
        """Export all data for an agent."""
        
        data = {
            "agent": await self._get_agent_data(agent_id),
            "wallet": await self._get_wallet_data(agent_id),
            "transactions": await self._get_transactions(
                agent_id, start_date, end_date
            ),
            "kyc": await self._get_kyc_data(agent_id),
            "risk_profile": await self._get_risk_profile(agent_id),
            "audit_logs": await self._get_audit_logs(
                agent_id, start_date, end_date
            ),
        }
        
        if format == "json":
            return self._export_json(data)
        elif format == "csv":
            return self._export_csv(data)
        elif format == "pdf":
            return self._export_pdf_report(data)
```

## Compliance API

### Endpoints

```
POST   /compliance/kyc/start              Start KYC verification
GET    /compliance/kyc/{user_id}/status   Get KYC status
POST   /compliance/aml/screen             Screen transaction
GET    /compliance/audit/{agent_id}       Get audit trail
POST   /compliance/export                 Export compliance data
GET    /compliance/restrictions           Get current restrictions
```

### Implementation

```python
router = APIRouter(prefix="/compliance", tags=["compliance"])

@router.post("/kyc/start")
async def start_kyc(
    request: KYCStartRequest,
    kyc_service: KYCService = Depends(get_kyc_service)
) -> KYCStartResponse:
    """Start KYC verification process."""
    result = await kyc_service.start_verification(
        user_id=request.user_id,
        tier=request.tier,
        country=request.country
    )
    return KYCStartResponse(
        transaction_id=result.transaction_id,
        redirect_url=result.redirect_url,
        expires_at=result.expires_at
    )

@router.post("/aml/screen")
async def screen_transaction(
    request: AMLScreenRequest,
    aml_service: AMLService = Depends(get_aml_service)
) -> AMLScreenResponse:
    """Screen a transaction for AML."""
    result = await aml_service.screen(
        transaction_id=request.transaction_id,
        from_address=request.from_address,
        to_address=request.to_address,
        amount=request.amount
    )
    return AMLScreenResponse(
        passed=result.passed,
        risk_score=result.risk_score,
        alerts=result.alerts
    )
```

## Compliance Checklist

### Pre-Launch

- [ ] KYC provider integrated and tested
- [ ] AML monitoring rules configured
- [ ] Sanctions screening enabled
- [ ] Geographic restrictions implemented
- [ ] Audit logging operational
- [ ] Data retention policies configured
- [ ] Privacy policy and ToS updated

### Ongoing

- [ ] Daily transaction monitoring review
- [ ] Weekly AML alert review
- [ ] Monthly compliance report
- [ ] Quarterly sanctions list update
- [ ] Annual compliance audit
- [ ] Staff training on AML/KYC

### Documentation

- [ ] Compliance program documented
- [ ] KYC/AML procedures written
- [ ] Risk assessment completed
- [ ] Incident response plan
- [ ] Regulatory contact list
- [ ] Legal counsel engaged

