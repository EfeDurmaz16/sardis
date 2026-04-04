"""Pydantic schemas for Sardis AgentKit actions."""
from pydantic import BaseModel, Field


class CreateAgentSchema(BaseModel):
    """Schema for creating an AI agent with a Sardis wallet."""
    name: str = Field(..., description="Name for the AI agent")
    description: str = Field("", description="What this agent does")


class SetPolicySchema(BaseModel):
    """Schema for setting a spending policy on an agent."""
    agent_id: str = Field(..., description="The Sardis agent ID")
    policy_text: str = Field(..., description="Natural language spending rules, e.g. 'Max $100/day, only SaaS tools'")


class SendPaymentSchema(BaseModel):
    """Schema for sending a policy-enforced payment."""
    agent_id: str = Field(..., description="The Sardis agent ID")
    amount: str = Field(..., description="Amount in whole units (e.g. '25.50')")
    currency: str = Field("USDC", description="Token symbol")
    recipient: str = Field(..., description="Recipient address or merchant name")
    memo: str = Field("", description="Payment memo / reason")


class CheckBalanceSchema(BaseModel):
    """Schema for checking wallet balance."""
    wallet_id: str = Field(..., description="The Sardis wallet ID")
