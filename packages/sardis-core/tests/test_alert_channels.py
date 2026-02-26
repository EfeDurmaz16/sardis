"""Tests for alert channels and dispatcher."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sardis_v2_core.alert_rules import Alert, AlertType, AlertSeverity
from sardis_v2_core.alert_channels import (
    AlertDispatcher,
    WebSocketChannel,
    SlackChannel,
    DiscordChannel,
    EmailChannel,
)


@pytest.fixture
def sample_alert():
    """Create a sample alert for testing."""
    return Alert(
        alert_type=AlertType.PAYMENT_EXECUTED,
        severity=AlertSeverity.WARNING,
        message="Test payment executed",
        agent_id="agent_123",
        organization_id="org_456",
        data={
            "amount": "1500.00",
            "transaction_id": "tx_abc",
        },
    )


def test_dispatcher_initialization():
    """Test dispatcher initialization."""
    dispatcher = AlertDispatcher()

    assert isinstance(dispatcher.channels, dict)
    assert isinstance(dispatcher.channel_configs, dict)
    assert len(dispatcher.channels) == 0


def test_dispatcher_register_channel():
    """Test registering a channel."""
    dispatcher = AlertDispatcher()

    # Create mock channel
    mock_channel = MagicMock()
    dispatcher.register_channel("test", mock_channel, enabled=True)

    assert "test" in dispatcher.channels
    assert dispatcher.channels["test"] == mock_channel
    assert dispatcher.channel_configs["test"].enabled is True


def test_dispatcher_unregister_channel():
    """Test unregistering a channel."""
    dispatcher = AlertDispatcher()

    mock_channel = MagicMock()
    dispatcher.register_channel("test", mock_channel)

    assert "test" in dispatcher.channels

    dispatcher.unregister_channel("test")

    assert "test" not in dispatcher.channels
    assert "test" not in dispatcher.channel_configs


def test_dispatcher_set_channel_enabled():
    """Test enabling/disabling a channel."""
    dispatcher = AlertDispatcher()

    mock_channel = MagicMock()
    dispatcher.register_channel("test", mock_channel, enabled=True)

    assert dispatcher.channel_configs["test"].enabled is True

    dispatcher.set_channel_enabled("test", False)

    assert dispatcher.channel_configs["test"].enabled is False


@pytest.mark.asyncio
async def test_dispatcher_dispatch_single_channel(sample_alert):
    """Test dispatching to a single channel."""
    dispatcher = AlertDispatcher()

    # Create mock channel
    mock_channel = AsyncMock()
    mock_channel.send = AsyncMock(return_value=True)

    dispatcher.register_channel("test", mock_channel)

    results = await dispatcher.dispatch(sample_alert, channels=["test"])

    assert results["test"] is True
    mock_channel.send.assert_called_once()


@pytest.mark.asyncio
async def test_dispatcher_dispatch_multiple_channels(sample_alert):
    """Test dispatching to multiple channels."""
    dispatcher = AlertDispatcher()

    # Create mock channels
    mock_channel1 = AsyncMock()
    mock_channel1.send = AsyncMock(return_value=True)

    mock_channel2 = AsyncMock()
    mock_channel2.send = AsyncMock(return_value=True)

    dispatcher.register_channel("channel1", mock_channel1)
    dispatcher.register_channel("channel2", mock_channel2)

    results = await dispatcher.dispatch(sample_alert)

    assert results["channel1"] is True
    assert results["channel2"] is True
    mock_channel1.send.assert_called_once()
    mock_channel2.send.assert_called_once()


@pytest.mark.asyncio
async def test_dispatcher_disabled_channel_not_called(sample_alert):
    """Test that disabled channels are not called."""
    dispatcher = AlertDispatcher()

    mock_channel = AsyncMock()
    mock_channel.send = AsyncMock(return_value=True)

    dispatcher.register_channel("test", mock_channel, enabled=False)

    results = await dispatcher.dispatch(sample_alert)

    assert len(results) == 0
    mock_channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_dispatcher_uses_severity_channel_map(sample_alert):
    """Critical/warning/info can route to different channel sets."""
    dispatcher = AlertDispatcher()

    websocket_channel = AsyncMock()
    websocket_channel.send = AsyncMock(return_value=True)
    pager_channel = AsyncMock()
    pager_channel.send = AsyncMock(return_value=True)

    dispatcher.register_channel("websocket", websocket_channel)
    dispatcher.register_channel("pager", pager_channel)
    dispatcher.set_severity_channel_map(
        {
            "warning": ["websocket"],
            "critical": ["websocket", "pager"],
        }
    )

    warning_alert = Alert(
        alert_type=AlertType.PAYMENT_EXECUTED,
        severity=AlertSeverity.WARNING,
        message="Warning",
        organization_id="org_456",
    )
    await dispatcher.dispatch(warning_alert)

    websocket_channel.send.assert_called_once()
    pager_channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_dispatcher_cooldown_suppresses_duplicate(sample_alert):
    """Duplicate alerts in cooldown window should not re-dispatch."""
    dispatcher = AlertDispatcher()
    slack_channel = AsyncMock()
    slack_channel.send = AsyncMock(return_value=True)
    dispatcher.register_channel("slack", slack_channel)
    dispatcher.set_channel_cooldowns({"slack": 120})

    first = await dispatcher.dispatch(sample_alert, channels=["slack"])
    second = await dispatcher.dispatch(sample_alert, channels=["slack"])

    assert first["slack"] is True
    assert second["slack"] is True
    slack_channel.send.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_channel_no_manager():
    """Test WebSocket channel without connection manager."""
    channel = WebSocketChannel(connection_manager=None)
    alert = Alert(
        alert_type=AlertType.PAYMENT_EXECUTED,
        severity=AlertSeverity.INFO,
        message="Test",
    )

    result = await channel.send(alert)

    assert result is False


@pytest.mark.asyncio
async def test_websocket_channel_with_manager():
    """Test WebSocket channel with connection manager."""
    mock_manager = AsyncMock()
    mock_manager.broadcast = AsyncMock()

    channel = WebSocketChannel(connection_manager=mock_manager)
    alert = Alert(
        alert_type=AlertType.PAYMENT_EXECUTED,
        severity=AlertSeverity.INFO,
        message="Test",
        organization_id="org_123",
    )

    result = await channel.send(alert)

    assert result is True
    mock_manager.broadcast.assert_called_once_with("org_123", alert.to_dict())


@pytest.mark.asyncio
async def test_slack_channel_send_success(sample_alert):
    """Test Slack channel send success."""
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        post_ctx = MagicMock()
        post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        post_ctx.__aexit__ = AsyncMock(return_value=None)
        session_ctx = MagicMock()
        session_ctx.post = MagicMock(return_value=post_ctx)
        mock_session.return_value.__aenter__.return_value = session_ctx

        channel = SlackChannel(webhook_url="https://hooks.slack.com/test")
        result = await channel.send(sample_alert)

        assert result is True


@pytest.mark.asyncio
async def test_discord_channel_send_success(sample_alert):
    """Test Discord channel send success."""
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        post_ctx = MagicMock()
        post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        post_ctx.__aexit__ = AsyncMock(return_value=None)
        session_ctx = MagicMock()
        session_ctx.post = MagicMock(return_value=post_ctx)
        mock_session.return_value.__aenter__.return_value = session_ctx

        channel = DiscordChannel(webhook_url="https://discord.com/api/webhooks/test")
        result = await channel.send(sample_alert)

        assert result is True


@pytest.mark.asyncio
async def test_email_channel_send_success(sample_alert):
    """Test Email channel send success."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        channel = EmailChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="test@example.com",
            smtp_password="password",
            from_email="alerts@sardis.sh",
            to_emails=["admin@example.com"],
        )

        result = await channel.send(sample_alert)

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()


@pytest.mark.asyncio
async def test_dispatcher_handles_channel_exception(sample_alert):
    """Test that dispatcher handles channel exceptions gracefully."""
    dispatcher = AlertDispatcher()

    # Create channel that raises exception
    mock_channel = AsyncMock()
    mock_channel.send = AsyncMock(side_effect=Exception("Test error"))

    dispatcher.register_channel("failing_channel", mock_channel)

    results = await dispatcher.dispatch(sample_alert)

    # Should return False for failed channel
    assert results["failing_channel"] is False


def test_alert_to_dict_serialization(sample_alert):
    """Test that alert can be serialized to dict."""
    alert_dict = sample_alert.to_dict()

    assert alert_dict["id"] == sample_alert.id
    assert alert_dict["alert_type"] == "payment_executed"
    assert alert_dict["severity"] == "warning"
    assert alert_dict["message"] == "Test payment executed"
    assert alert_dict["agent_id"] == "agent_123"
    assert alert_dict["organization_id"] == "org_456"
    assert "timestamp" in alert_dict
    assert alert_dict["data"]["amount"] == "1500.00"
