"""Tests for sardis_api.email_templates module."""
from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis_api.email_templates import (
    _kyc_status_html,
    _payment_notification_html,
    _plan_upgrade_html,
    _policy_block_html,
    _welcome_html,
    send_email,
    send_kyc_status_email,
    send_payment_notification,
    send_plan_upgrade_email,
    send_policy_block_notification,
    send_welcome_email,
)

# ---------------------------------------------------------------------------
# send_email — no-op without SMTP_HOST
# ---------------------------------------------------------------------------

class TestSendEmailNoOp:
    @pytest.mark.asyncio
    async def test_returns_false_without_smtp_host(self):
        """send_email must be a no-op (return False) when SMTP_HOST is unset."""
        env = {k: v for k, v in os.environ.items() if k != "SMTP_HOST"}
        with patch.dict(os.environ, env, clear=True):
            result = await send_email("user@example.com", "Test", "<p>Hello</p>")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_with_empty_smtp_host(self):
        with patch.dict(os.environ, {"SMTP_HOST": ""}, clear=False):
            result = await send_email("user@example.com", "Test", "<p>Hello</p>")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_smtp_succeeds(self):
        """send_email returns True when the SMTP send succeeds."""
        import asyncio as _asyncio

        smtp_env = {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_FROM_EMAIL": "noreply@sardis.sh",
        }
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=None)
        with patch.dict(os.environ, smtp_env, clear=False):
            with patch("sardis_api.email_templates.asyncio") as mock_asyncio:
                mock_asyncio.get_event_loop.return_value = mock_loop
                result = await send_email(
                    "user@example.com",
                    "Hello",
                    "<p>Hello</p>",
                )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_smtp_raises(self):
        """send_email returns False (does not raise) when SMTP raises an exception."""
        smtp_env = {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user",
            "SMTP_PASSWORD": "pass",
        }
        with patch.dict(os.environ, smtp_env, clear=False):
            with patch("asyncio.get_event_loop") as mock_loop:
                import asyncio
                mock_loop.return_value.run_in_executor = AsyncMock(
                    side_effect=ConnectionRefusedError("refused")
                )
                result = await send_email("user@example.com", "Test", "<p>Hi</p>")
        assert result is False


# ---------------------------------------------------------------------------
# Helper functions do not raise
# ---------------------------------------------------------------------------

class TestTemplateHelpers:
    def test_welcome_html_does_not_raise(self):
        html = _welcome_html("test_api_key_placeholder")
        assert isinstance(html, str)
        assert len(html) > 100

    def test_payment_notification_html_does_not_raise(self):
        html = _payment_notification_html(
            agent_name="BuyBot",
            amount=42.50,
            merchant="Acme Corp",
            tx_id="txn_abc123",
        )
        assert isinstance(html, str)

    def test_policy_block_html_does_not_raise(self):
        html = _policy_block_html(
            agent_name="SpendBot",
            amount=1000.0,
            reason="Exceeds daily limit of $500",
        )
        assert isinstance(html, str)

    def test_kyc_status_html_approved(self):
        html = _kyc_status_html("approved")
        assert "approved" in html.lower() or "verified" in html.lower()

    def test_kyc_status_html_rejected(self):
        html = _kyc_status_html("rejected")
        assert "failed" in html.lower() or "rejected" in html.lower()

    def test_kyc_status_html_pending(self):
        html = _kyc_status_html("pending")
        assert "review" in html.lower() or "pending" in html.lower()

    def test_plan_upgrade_html_does_not_raise(self):
        html = _plan_upgrade_html("growth")
        assert isinstance(html, str)

    def test_all_templates_include_sardis_branding(self):
        templates = [
            _welcome_html("test_api_key_placeholder"),
            _payment_notification_html("A", 10.0, "B", "txn_1"),
            _policy_block_html("A", 10.0, "limit exceeded"),
            _kyc_status_html("pending"),
            _plan_upgrade_html("pro"),
        ]
        for html in templates:
            assert "Sardis" in html, "Template missing Sardis branding"
            assert "sardis.sh" in html, "Template missing sardis.sh link"


# ---------------------------------------------------------------------------
# Welcome email template content
# ---------------------------------------------------------------------------

class TestWelcomeEmailTemplate:
    def test_contains_api_key_prefix(self):
        prefix = "test_api_key_placeholder"
        html = _welcome_html(prefix)
        assert prefix in html

    def test_contains_dashboard_link(self):
        html = _welcome_html("test_api_key_placeholder")
        assert "app.sardis.sh" in html

    def test_contains_docs_link(self):
        html = _welcome_html("test_api_key_placeholder")
        assert "sardis.sh/docs" in html

    def test_mentions_test_mode(self):
        html = _welcome_html("test_api_key_placeholder")
        assert "test mode" in html.lower() or "test" in html.lower()


# ---------------------------------------------------------------------------
# Payment notification template content
# ---------------------------------------------------------------------------

class TestPaymentNotificationTemplate:
    def test_contains_agent_name(self):
        html = _payment_notification_html("MyAgent", 99.99, "Shop", "txn_001")
        assert "MyAgent" in html

    def test_contains_merchant(self):
        html = _payment_notification_html("Agent", 10.0, "AcmeCorp", "txn_002")
        assert "AcmeCorp" in html

    def test_contains_amount(self):
        html = _payment_notification_html("Agent", 12.50, "Shop", "txn_003")
        assert "12.50" in html

    def test_contains_tx_id(self):
        html = _payment_notification_html("Agent", 5.0, "Shop", "txn_unique_99")
        assert "txn_unique_99" in html


# ---------------------------------------------------------------------------
# Policy block template content
# ---------------------------------------------------------------------------

class TestPolicyBlockTemplate:
    def test_contains_reason(self):
        html = _policy_block_html("Bot", 250.0, "daily_limit_exceeded")
        assert "daily_limit_exceeded" in html

    def test_contains_amount(self):
        html = _policy_block_html("Bot", 250.0, "some reason")
        assert "250.00" in html

    def test_contains_agent_name(self):
        html = _policy_block_html("MyBotName", 10.0, "reason")
        assert "MyBotName" in html


# ---------------------------------------------------------------------------
# Async helper wrappers do not raise
# ---------------------------------------------------------------------------

class TestAsyncHelpers:
    @pytest.mark.asyncio
    async def test_send_welcome_email_noop(self):
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise regardless of SMTP config
            await send_welcome_email("test@example.com", "test_api_key_placeholder")

    @pytest.mark.asyncio
    async def test_send_payment_notification_noop(self):
        with patch.dict(os.environ, {}, clear=True):
            await send_payment_notification(
                email="test@example.com",
                agent_name="BotA",
                amount=50.0,
                merchant="Acme",
                tx_id="txn_x",
            )

    @pytest.mark.asyncio
    async def test_send_policy_block_notification_noop(self):
        with patch.dict(os.environ, {}, clear=True):
            await send_policy_block_notification(
                email="test@example.com",
                agent_name="BotB",
                amount=1000.0,
                reason="Over limit",
            )

    @pytest.mark.asyncio
    async def test_send_kyc_status_email_noop(self):
        with patch.dict(os.environ, {}, clear=True):
            await send_kyc_status_email("test@example.com", "approved")

    @pytest.mark.asyncio
    async def test_send_plan_upgrade_email_noop(self):
        with patch.dict(os.environ, {}, clear=True):
            await send_plan_upgrade_email("test@example.com", "growth")
