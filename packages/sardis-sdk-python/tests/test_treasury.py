"""Tests for TreasuryResource."""
from __future__ import annotations

from sardis_sdk.models.treasury import (
    CreateExternalBankAccountRequest,
    TreasuryPaymentRequest,
    VerifyMicroDepositsRequest,
)


async def test_list_financial_accounts(client, httpx_mock):
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/treasury/financial-accounts?refresh=false",
        method="GET",
        json=[
            {
                "organization_id": "org_test",
                "financial_account_token": "fa_123",
                "account_token": "acct_123",
                "account_role": "ISSUING",
                "currency": "USD",
                "status": "OPEN",
                "is_program_level": False,
            }
        ],
    )

    result = await client.treasury.list_financial_accounts()
    assert len(result) == 1
    assert result[0].financial_account_token == "fa_123"
    assert result[0].account_role == "ISSUING"


async def test_create_external_bank_account(client, httpx_mock):
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/treasury/external-bank-accounts",
        method="POST",
        json={
            "organization_id": "org_test",
            "external_bank_account_token": "eba_123",
            "financial_account_token": "fa_123",
            "owner_type": "BUSINESS",
            "owner": "Sardis Labs LLC",
            "account_type": "CHECKING",
            "verification_method": "MICRO_DEPOSIT",
            "verification_state": "PENDING",
            "state": "ENABLED",
            "currency": "USD",
            "country": "USA",
            "is_paused": False,
            "metadata": {},
        },
    )

    result = await client.treasury.create_external_bank_account(
        CreateExternalBankAccountRequest(
            financial_account_token="fa_123",
            owner="Sardis Labs LLC",
            routing_number="021000021",
            account_number="123456789",
        )
    )
    assert result.external_bank_account_token == "eba_123"
    assert result.verification_state == "PENDING"


async def test_verify_micro_deposits(client, httpx_mock):
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/treasury/external-bank-accounts/eba_123/verify-micro-deposits",
        method="POST",
        json={
            "organization_id": "org_test",
            "external_bank_account_token": "eba_123",
            "financial_account_token": "fa_123",
            "owner_type": "BUSINESS",
            "owner": "Sardis Labs LLC",
            "account_type": "CHECKING",
            "verification_method": "MICRO_DEPOSIT",
            "verification_state": "ENABLED",
            "state": "ENABLED",
            "currency": "USD",
            "country": "USA",
            "is_paused": False,
            "metadata": {},
        },
    )

    result = await client.treasury.verify_micro_deposits(
        "eba_123",
        VerifyMicroDepositsRequest(micro_deposits=["19", "89"]),
    )
    assert result.verification_state == "ENABLED"


async def test_fund_payment(client, httpx_mock):
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/treasury/fund",
        method="POST",
        json={
            "payment_token": "pay_123",
            "status": "PENDING",
            "result": "APPROVED",
            "direction": "DEBIT",
            "method": "ACH_NEXT_DAY",
            "currency": "USD",
            "pending_amount": 5000,
            "settled_amount": 0,
            "financial_account_token": "fa_123",
            "external_bank_account_token": "eba_123",
        },
    )

    result = await client.treasury.fund(
        TreasuryPaymentRequest(
            financial_account_token="fa_123",
            external_bank_account_token="eba_123",
            amount_minor=5000,
            sec_code="CCD",
        )
    )
    assert result.payment_token == "pay_123"
    assert result.pending_amount == 5000
