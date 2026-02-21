"""Unit tests for emergency kill switch."""

import pytest
import asyncio
from sardis_guardrails.kill_switch import (
    KillSwitch,
    KillSwitchError,
    ActivationReason,
    get_kill_switch,
)


class TestKillSwitch:
    """Test kill switch activation and scope management."""

    @pytest.mark.asyncio
    async def test_global_scope_activation(self):
        """Test global kill switch blocks all agents."""
        kill_switch = KillSwitch()

        await kill_switch.activate_global(
            reason=ActivationReason.MANUAL,
            activated_by="admin-123",
            notes="Emergency shutdown",
        )

        # Should block any agent in any org
        with pytest.raises(KillSwitchError) as exc_info:
            await kill_switch.check(agent_id="agent-1", org_id="org-1")

        assert "Global kill switch active" in str(exc_info.value)
        assert "manual" in str(exc_info.value).lower()

        # Should block different agent/org too
        with pytest.raises(KillSwitchError):
            await kill_switch.check(agent_id="agent-2", org_id="org-2")

    @pytest.mark.asyncio
    async def test_organization_scope_activation(self):
        """Test organization kill switch blocks only org agents."""
        kill_switch = KillSwitch()

        await kill_switch.activate_organization(
            org_id="org-blocked",
            reason=ActivationReason.COMPLIANCE,
            activated_by="compliance-system",
            notes="KYC verification failed",
        )

        # Should block agents in the organization
        with pytest.raises(KillSwitchError) as exc_info:
            await kill_switch.check(agent_id="agent-1", org_id="org-blocked")

        assert "Organization kill switch active" in str(exc_info.value)
        assert "org-blocked" in str(exc_info.value)

        # Should NOT block agents in other organizations
        await kill_switch.check(agent_id="agent-2", org_id="org-allowed")  # No error

    @pytest.mark.asyncio
    async def test_agent_scope_activation(self):
        """Test agent-specific kill switch."""
        kill_switch = KillSwitch()

        await kill_switch.activate_agent(
            agent_id="agent-suspicious",
            reason=ActivationReason.FRAUD,
            activated_by="fraud-detector",
            notes="Unusual spending pattern detected",
        )

        # Should block the specific agent
        with pytest.raises(KillSwitchError) as exc_info:
            await kill_switch.check(agent_id="agent-suspicious", org_id="org-1")

        assert "Agent kill switch active" in str(exc_info.value)
        assert "agent-suspicious" in str(exc_info.value)

        # Should NOT block other agents
        await kill_switch.check(agent_id="agent-normal", org_id="org-1")  # No error

    @pytest.mark.asyncio
    async def test_global_deactivation(self):
        """Test deactivating global kill switch."""
        kill_switch = KillSwitch()

        await kill_switch.activate_global(
            reason=ActivationReason.MANUAL,
            activated_by="admin",
        )

        # Verify it's active
        assert await kill_switch.is_active_global() is True

        # Deactivate
        await kill_switch.deactivate_global()

        # Should no longer block
        await kill_switch.check(agent_id="agent-1", org_id="org-1")  # No error
        assert await kill_switch.is_active_global() is False

    @pytest.mark.asyncio
    async def test_organization_deactivation(self):
        """Test deactivating organization kill switch."""
        kill_switch = KillSwitch()

        await kill_switch.activate_organization(
            org_id="org-1",
            reason=ActivationReason.MANUAL,
        )

        assert await kill_switch.is_active_organization("org-1") is True

        await kill_switch.deactivate_organization("org-1")

        await kill_switch.check(agent_id="agent-1", org_id="org-1")  # No error
        assert await kill_switch.is_active_organization("org-1") is False

    @pytest.mark.asyncio
    async def test_agent_deactivation(self):
        """Test deactivating agent kill switch."""
        kill_switch = KillSwitch()

        await kill_switch.activate_agent(
            agent_id="agent-1",
            reason=ActivationReason.ANOMALY,
        )

        assert await kill_switch.is_active_agent("agent-1") is True

        await kill_switch.deactivate_agent("agent-1")

        await kill_switch.check(agent_id="agent-1", org_id="org-1")  # No error
        assert await kill_switch.is_active_agent("agent-1") is False

    @pytest.mark.asyncio
    async def test_auto_reactivation_timeout_global(self):
        """Test automatic reactivation after timeout for global switch."""
        kill_switch = KillSwitch()

        # Activate with 0.1 second auto-reactivation
        await kill_switch.activate_global(
            reason=ActivationReason.RATE_LIMIT,
            auto_reactivate_after=0.1,
        )

        # Should be active initially
        assert await kill_switch.is_active_global() is True

        # Wait for auto-reactivation
        await asyncio.sleep(0.15)

        # Should be automatically deactivated
        assert await kill_switch.is_active_global() is False
        await kill_switch.check(agent_id="agent-1", org_id="org-1")  # No error

    @pytest.mark.asyncio
    async def test_auto_reactivation_timeout_organization(self):
        """Test automatic reactivation for organization switch."""
        kill_switch = KillSwitch()

        await kill_switch.activate_organization(
            org_id="org-temp",
            reason=ActivationReason.RATE_LIMIT,
            auto_reactivate_after=0.1,
        )

        assert await kill_switch.is_active_organization("org-temp") is True

        await asyncio.sleep(0.15)

        assert await kill_switch.is_active_organization("org-temp") is False

    @pytest.mark.asyncio
    async def test_auto_reactivation_timeout_agent(self):
        """Test automatic reactivation for agent switch."""
        kill_switch = KillSwitch()

        await kill_switch.activate_agent(
            agent_id="agent-temp",
            reason=ActivationReason.POLICY_VIOLATION,
            auto_reactivate_after=0.1,
        )

        assert await kill_switch.is_active_agent("agent-temp") is True

        await asyncio.sleep(0.15)

        assert await kill_switch.is_active_agent("agent-temp") is False

    @pytest.mark.asyncio
    async def test_get_active_switches(self):
        """Test retrieving all active switches."""
        kill_switch = KillSwitch()

        await kill_switch.activate_global(reason=ActivationReason.MANUAL)
        await kill_switch.activate_organization("org-1", reason=ActivationReason.FRAUD)
        await kill_switch.activate_agent("agent-1", reason=ActivationReason.ANOMALY)

        active = await kill_switch.get_active_switches()

        assert active["global"] is not None
        assert "org-1" in active["organizations"]
        assert "agent-1" in active["agents"]

    @pytest.mark.asyncio
    async def test_activation_reasons(self):
        """Test different activation reasons are recorded."""
        kill_switch = KillSwitch()

        await kill_switch.activate_agent(
            agent_id="agent-1",
            reason=ActivationReason.FRAUD,
            activated_by="fraud-system",
            notes="Multiple failed auth attempts",
        )

        with pytest.raises(KillSwitchError) as exc_info:
            await kill_switch.check(agent_id="agent-1", org_id="org-1")

        error_msg = str(exc_info.value)
        assert "fraud" in error_msg.lower()
        assert "Multiple failed auth attempts" in error_msg

    @pytest.mark.asyncio
    async def test_precedence_global_over_org(self):
        """Test global kill switch takes precedence over org-specific."""
        kill_switch = KillSwitch()

        await kill_switch.activate_organization("org-1", reason=ActivationReason.MANUAL)
        await kill_switch.activate_global(reason=ActivationReason.COMPLIANCE)

        # Should raise error mentioning global, not org
        with pytest.raises(KillSwitchError) as exc_info:
            await kill_switch.check(agent_id="agent-1", org_id="org-1")

        assert "Global kill switch active" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_precedence_org_over_agent(self):
        """Test org kill switch takes precedence over agent-specific."""
        kill_switch = KillSwitch()

        await kill_switch.activate_agent("agent-1", reason=ActivationReason.MANUAL)
        await kill_switch.activate_organization("org-1", reason=ActivationReason.FRAUD)

        # Should raise error mentioning org, not agent
        with pytest.raises(KillSwitchError) as exc_info:
            await kill_switch.check(agent_id="agent-1", org_id="org-1")

        assert "Organization kill switch active" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_kill_switch_singleton(self):
        """Test global singleton instance."""
        instance1 = get_kill_switch()
        instance2 = get_kill_switch()

        assert instance1 is instance2

    @pytest.mark.asyncio
    async def test_multiple_organizations(self):
        """Test multiple organization kill switches."""
        kill_switch = KillSwitch()

        await kill_switch.activate_organization("org-1", reason=ActivationReason.MANUAL)
        await kill_switch.activate_organization("org-2", reason=ActivationReason.FRAUD)

        # org-1 blocked
        with pytest.raises(KillSwitchError):
            await kill_switch.check(agent_id="agent-1", org_id="org-1")

        # org-2 blocked
        with pytest.raises(KillSwitchError):
            await kill_switch.check(agent_id="agent-2", org_id="org-2")

        # org-3 allowed
        await kill_switch.check(agent_id="agent-3", org_id="org-3")

    @pytest.mark.asyncio
    async def test_multiple_agents(self):
        """Test multiple agent kill switches."""
        kill_switch = KillSwitch()

        await kill_switch.activate_agent("agent-1", reason=ActivationReason.ANOMALY)
        await kill_switch.activate_agent("agent-2", reason=ActivationReason.FRAUD)

        # agent-1 blocked
        with pytest.raises(KillSwitchError):
            await kill_switch.check(agent_id="agent-1", org_id="org-1")

        # agent-2 blocked
        with pytest.raises(KillSwitchError):
            await kill_switch.check(agent_id="agent-2", org_id="org-1")

        # agent-3 allowed
        await kill_switch.check(agent_id="agent-3", org_id="org-1")
