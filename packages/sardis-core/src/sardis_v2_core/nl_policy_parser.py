"""Natural Language Policy Parser for Sardis.

This module enables parsing of natural language spending policies into structured
SpendingPolicy objects. It uses OpenAI's GPT models via the Instructor library
for accurate extraction of spending constraints.

Example:
    >>> parser = NLPolicyParser(api_key="sk-...")
    >>> policy = await parser.parse("spend max $500 per day on AWS, block gambling")
    >>> print(policy.spending_limits[0].max_amount)
    500.0
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional, List, Any
import uuid
import logging

try:
    import instructor
    from openai import OpenAI, AsyncOpenAI
    HAS_INSTRUCTOR = True
except ImportError:
    HAS_INSTRUCTOR = False

try:
    from pydantic import BaseModel, Field, field_validator
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

from .spending_policy import (
    SpendingPolicy,
    TimeWindowLimit,
    MerchantRule,
    TrustLevel,
    SpendingScope,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for LLM Extraction
# ============================================================================

if HAS_PYDANTIC:
    class ExtractedSpendingLimit(BaseModel):
        """A single spending limit extracted from natural language."""

        vendor_pattern: str = Field(
            description="Vendor name, domain, or pattern (e.g., 'AWS', 'openai.com', '*cloud*')"
        )
        max_amount: float = Field(
            gt=0,
            description="Maximum amount in the specified currency"
        )
        period: Literal["per_transaction", "daily", "weekly", "monthly"] = Field(
            default="daily",
            description="Time period for the limit"
        )
        currency: str = Field(
            default="USD",
            description="Currency code (USD, EUR, etc.)"
        )

        @field_validator('vendor_pattern')
        @classmethod
        def normalize_vendor(cls, v: str) -> str:
            """Normalize vendor names to lowercase."""
            return v.strip().lower()

    class ExtractedCategoryRestriction(BaseModel):
        """Category-based spending restrictions."""

        allowed_categories: List[str] = Field(
            default_factory=list,
            description="List of allowed merchant categories"
        )
        blocked_categories: List[str] = Field(
            default_factory=list,
            description="List of blocked merchant categories (e.g., 'gambling', 'adult')"
        )

    class ExtractedTimeRestriction(BaseModel):
        """Time-based spending restrictions."""

        allowed_hours_start: int = Field(
            ge=0, le=23, default=0,
            description="Start hour (0-23) for allowed spending window"
        )
        allowed_hours_end: int = Field(
            ge=0, le=23, default=23,
            description="End hour (0-23) for allowed spending window"
        )
        allowed_days: List[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]] = Field(
            default_factory=lambda: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            description="Days of week when spending is allowed"
        )
        timezone: str = Field(
            default="UTC",
            description="Timezone for time restrictions"
        )

    class ExtractedPolicy(BaseModel):
        """Complete spending policy extracted from natural language."""

        name: str = Field(
            description="Human-readable policy name derived from the input"
        )
        description: str = Field(
            description="Original natural language input or summary"
        )
        spending_limits: List[ExtractedSpendingLimit] = Field(
            default_factory=list,
            description="List of spending limits per vendor/category"
        )
        category_restrictions: Optional[ExtractedCategoryRestriction] = Field(
            default=None,
            description="Category-based restrictions if specified"
        )
        time_restrictions: Optional[ExtractedTimeRestriction] = Field(
            default=None,
            description="Time-based restrictions if specified"
        )
        requires_approval_above: Optional[float] = Field(
            default=None,
            description="Amount threshold requiring manual approval"
        )
        global_daily_limit: Optional[float] = Field(
            default=None,
            description="Global daily spending limit across all vendors"
        )
        global_monthly_limit: Optional[float] = Field(
            default=None,
            description="Global monthly spending limit across all vendors"
        )
        is_active: bool = Field(
            default=True,
            description="Whether the policy is active"
        )


# ============================================================================
# Policy Parser Implementation
# ============================================================================

class NLPolicyParser:
    """
    Natural Language Policy Parser.

    Converts natural language spending policies into structured SpendingPolicy objects.
    Uses OpenAI GPT models via the Instructor library for accurate extraction.

    Example:
        >>> parser = NLPolicyParser(api_key="sk-...")
        >>> policy = await parser.parse("spend max $500 per day on AWS")
        >>> print(policy.spending_limits[0].max_amount)
        500.0
    """

    SYSTEM_PROMPT = """You are a financial policy parser for AI agent spending controls.
Your job is to convert natural language spending policies into structured JSON.

IMPORTANT RULES:
1. Extract ALL constraints mentioned in the input
2. Be precise with amounts (e.g., "$500" = 500.0, "five hundred" = 500.0)
3. Infer reasonable periods if not specified (default to "daily")
4. Recognize common merchant names and categories
5. Handle complex compound policies with multiple constraints
6. If a global limit is mentioned without a vendor, use global_daily_limit or global_monthly_limit

COMMON PATTERNS:
- "max $X per day" → daily limit
- "up to $X weekly" → weekly limit
- "spend limit $X" → per_transaction limit
- "only on [vendors]" → spending_limits with those vendors
- "block [category]" → blocked_categories
- "require approval over $X" → requires_approval_above
- "business hours only" → time_restrictions with hours 9-17
- "weekdays only" → allowed_days = ["mon", "tue", "wed", "thu", "fri"]

MERCHANT CATEGORIES:
- cloud: AWS, Azure, GCP, DigitalOcean, Vercel, Netlify
- ai: OpenAI, Anthropic, Cohere, Replicate
- saas: Slack, Notion, GitHub, Jira, Figma
- gambling: casinos, betting sites
- adult: adult content sites
- crypto: exchanges, DeFi platforms

Extract the policy accurately and completely."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.1,
    ):
        """
        Initialize the NL Policy Parser.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: Model to use for parsing (default: gpt-4o)
            temperature: Temperature for generation (default: 0.1 for consistency)
        """
        if not HAS_INSTRUCTOR:
            raise ImportError(
                "instructor package required for NL policy parsing. "
                "Install with: pip install instructor openai"
            )

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY or pass api_key.")

        self.model = model
        self.temperature = temperature

        # Initialize sync and async clients
        self._sync_client = instructor.from_openai(OpenAI(api_key=self.api_key))
        self._async_client = instructor.from_openai(AsyncOpenAI(api_key=self.api_key))

    def parse_sync(self, natural_language_policy: str) -> ExtractedPolicy:
        """
        Parse natural language policy synchronously.

        Args:
            natural_language_policy: Natural language description of spending policy

        Returns:
            ExtractedPolicy with structured constraints
        """
        return self._sync_client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_model=ExtractedPolicy,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Parse this policy: {natural_language_policy}"}
            ]
        )

    async def parse(self, natural_language_policy: str) -> ExtractedPolicy:
        """
        Parse natural language policy asynchronously.

        Args:
            natural_language_policy: Natural language description of spending policy

        Returns:
            ExtractedPolicy with structured constraints
        """
        return await self._async_client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_model=ExtractedPolicy,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Parse this policy: {natural_language_policy}"}
            ]
        )

    def to_spending_policy(
        self,
        extracted: ExtractedPolicy,
        agent_id: str = "",
    ) -> SpendingPolicy:
        """
        Convert ExtractedPolicy to SpendingPolicy domain object.

        Args:
            extracted: ExtractedPolicy from parse()
            agent_id: Agent ID to associate with the policy

        Returns:
            SpendingPolicy object ready for enforcement
        """
        # Start with a base policy
        policy = SpendingPolicy(
            policy_id=f"policy_{uuid.uuid4().hex[:16]}",
            agent_id=agent_id,
            trust_level=TrustLevel.MEDIUM,  # Default, can be adjusted
            require_preauth=extracted.requires_approval_above is not None,
        )

        # Set global limits if specified
        if extracted.global_daily_limit:
            policy.daily_limit = TimeWindowLimit(
                window_type="daily",
                limit_amount=Decimal(str(extracted.global_daily_limit)),
            )

        if extracted.global_monthly_limit:
            policy.monthly_limit = TimeWindowLimit(
                window_type="monthly",
                limit_amount=Decimal(str(extracted.global_monthly_limit)),
            )

        # Add merchant rules from spending limits
        for limit in extracted.spending_limits:
            # Add as allow rule with limit
            rule = MerchantRule(
                rule_type="allow",
                merchant_id=limit.vendor_pattern,
                max_per_tx=Decimal(str(limit.max_amount)) if limit.period == "per_transaction" else None,
                daily_limit=Decimal(str(limit.max_amount)) if limit.period == "daily" else None,
                reason=f"NL policy: max ${limit.max_amount} {limit.period}",
            )
            policy.merchant_rules.append(rule)

            # Set appropriate time window limit
            if limit.period == "daily" and not policy.daily_limit:
                policy.daily_limit = TimeWindowLimit(
                    window_type="daily",
                    limit_amount=Decimal(str(limit.max_amount)),
                )
            elif limit.period == "weekly" and not policy.weekly_limit:
                policy.weekly_limit = TimeWindowLimit(
                    window_type="weekly",
                    limit_amount=Decimal(str(limit.max_amount)),
                )
            elif limit.period == "monthly" and not policy.monthly_limit:
                policy.monthly_limit = TimeWindowLimit(
                    window_type="monthly",
                    limit_amount=Decimal(str(limit.max_amount)),
                )
            elif limit.period == "per_transaction":
                if Decimal(str(limit.max_amount)) < policy.limit_per_tx:
                    policy.limit_per_tx = Decimal(str(limit.max_amount))

        # Add category restrictions as deny rules
        if extracted.category_restrictions:
            for blocked_cat in extracted.category_restrictions.blocked_categories:
                rule = MerchantRule(
                    rule_type="deny",
                    category=blocked_cat.lower(),
                    reason=f"NL policy: blocked category",
                )
                policy.merchant_rules.insert(0, rule)  # Deny rules first

        # Handle approval threshold
        if extracted.requires_approval_above:
            policy.require_preauth = True
            # Store approval threshold (could add to SpendingPolicy if needed)

        return policy

    async def parse_and_convert(
        self,
        natural_language_policy: str,
        agent_id: str = "",
    ) -> SpendingPolicy:
        """
        Parse natural language and convert to SpendingPolicy in one step.

        Args:
            natural_language_policy: Natural language description
            agent_id: Agent ID to associate with the policy

        Returns:
            SpendingPolicy object ready for enforcement
        """
        extracted = await self.parse(natural_language_policy)
        return self.to_spending_policy(extracted, agent_id)


# ============================================================================
# Fallback Regex Parser (for when LLM is unavailable)
# ============================================================================

class RegexPolicyParser:
    """
    Fallback regex-based policy parser.

    Handles common patterns without LLM dependency. Less accurate but
    works offline and is faster for simple policies.
    """

    AMOUNT_PATTERN = re.compile(r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)')
    PERIOD_PATTERN = re.compile(r'\b(per\s+)?(transaction|daily|weekly|monthly|day|week|month)\b', re.I)
    VENDOR_PATTERN = re.compile(r'\b(?:on|for|at)\s+([A-Za-z0-9_\-\.]+)', re.I)
    BLOCK_PATTERN = re.compile(r'\bblock(?:ed|ing)?\s+([A-Za-z0-9_\-\s,]+)', re.I)
    APPROVAL_PATTERN = re.compile(r'\b(?:require|need)s?\s+approval\s+(?:above|over|for)\s+\$?([\d,]+)', re.I)

    def parse(self, natural_language_policy: str) -> dict:
        """
        Parse policy using regex patterns.

        Returns dict with extracted fields (not full ExtractedPolicy).
        """
        result = {
            "spending_limits": [],
            "blocked_categories": [],
            "requires_approval_above": None,
        }

        # Extract amounts
        amounts = self.AMOUNT_PATTERN.findall(natural_language_policy)
        amounts = [float(a.replace(",", "")) for a in amounts]

        # Extract period
        period_match = self.PERIOD_PATTERN.search(natural_language_policy)
        period = "daily"
        if period_match:
            p = period_match.group(2).lower()
            if p in ("transaction",):
                period = "per_transaction"
            elif p in ("day", "daily"):
                period = "daily"
            elif p in ("week", "weekly"):
                period = "weekly"
            elif p in ("month", "monthly"):
                period = "monthly"

        # Extract vendor
        vendor_match = self.VENDOR_PATTERN.search(natural_language_policy)
        vendor = vendor_match.group(1) if vendor_match else "*"

        # Build spending limit
        if amounts:
            result["spending_limits"].append({
                "vendor_pattern": vendor.lower(),
                "max_amount": amounts[0],
                "period": period,
                "currency": "USD",
            })

        # Extract blocked categories
        block_match = self.BLOCK_PATTERN.search(natural_language_policy)
        if block_match:
            categories = [c.strip().lower() for c in block_match.group(1).split(",")]
            result["blocked_categories"] = categories

        # Extract approval threshold
        approval_match = self.APPROVAL_PATTERN.search(natural_language_policy)
        if approval_match:
            result["requires_approval_above"] = float(approval_match.group(1).replace(",", ""))

        return result


# ============================================================================
# Factory Function
# ============================================================================

def create_policy_parser(
    use_llm: bool = True,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
) -> NLPolicyParser | RegexPolicyParser:
    """
    Create appropriate policy parser based on configuration.

    Args:
        use_llm: Whether to use LLM-based parsing (requires OpenAI API key)
        api_key: OpenAI API key (optional if use_llm=False)
        model: Model to use for LLM parsing

    Returns:
        Policy parser instance
    """
    if use_llm:
        try:
            return NLPolicyParser(api_key=api_key, model=model)
        except (ImportError, ValueError) as e:
            logger.warning(f"Failed to create LLM parser, falling back to regex: {e}")
            return RegexPolicyParser()
    else:
        return RegexPolicyParser()


# ============================================================================
# Convenience Functions
# ============================================================================

async def parse_nl_policy(
    natural_language: str,
    agent_id: str = "",
    api_key: Optional[str] = None,
) -> SpendingPolicy:
    """
    Convenience function to parse natural language and return SpendingPolicy.

    Args:
        natural_language: Natural language policy description
        agent_id: Agent ID to associate with policy
        api_key: OpenAI API key (optional, uses env var if not provided)

    Returns:
        SpendingPolicy object ready for enforcement

    Example:
        >>> policy = await parse_nl_policy("spend max $500 per day on AWS")
        >>> policy.daily_limit.limit_amount
        Decimal('500.00')
    """
    parser = NLPolicyParser(api_key=api_key)
    return await parser.parse_and_convert(natural_language, agent_id)


def parse_nl_policy_sync(
    natural_language: str,
    agent_id: str = "",
    api_key: Optional[str] = None,
) -> SpendingPolicy:
    """
    Synchronous version of parse_nl_policy.

    Args:
        natural_language: Natural language policy description
        agent_id: Agent ID to associate with policy
        api_key: OpenAI API key (optional, uses env var if not provided)

    Returns:
        SpendingPolicy object ready for enforcement
    """
    parser = NLPolicyParser(api_key=api_key)
    extracted = parser.parse_sync(natural_language)
    return parser.to_spending_policy(extracted, agent_id)
