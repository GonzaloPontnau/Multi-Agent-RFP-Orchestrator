"""
Unit tests for AgentFactory.

Tests the factory pattern implementation for creating specialist agents.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.agent_factory import AgentFactory
from app.agents.base import BaseSpecialistAgent
from app.agents.specialists import (
    FinancialSpecialistAgent,
    LegalSpecialistAgent,
    TechnicalSpecialistAgent,
    TimelineSpecialistAgent,
    RequirementsSpecialistAgent,
    GeneralSpecialistAgent,
)


class TestAgentFactoryCreation:
    """Tests for AgentFactory.create() method."""

    def test_create_financial_agent(self, test_factory):
        """Factory should create FinancialSpecialistAgent for 'financial' domain."""
        agent = test_factory.create("financial")
        
        assert isinstance(agent, FinancialSpecialistAgent)
        assert isinstance(agent, BaseSpecialistAgent)
        assert agent.domain == "financial"

    def test_create_legal_agent(self, test_factory):
        """Factory should create LegalSpecialistAgent for 'legal' domain."""
        agent = test_factory.create("legal")
        
        assert isinstance(agent, LegalSpecialistAgent)
        assert isinstance(agent, BaseSpecialistAgent)
        assert agent.domain == "legal"

    def test_create_technical_agent(self, test_factory):
        """Factory should create TechnicalSpecialistAgent for 'technical' domain."""
        agent = test_factory.create("technical")
        
        assert isinstance(agent, TechnicalSpecialistAgent)
        assert agent.domain == "technical"

    def test_create_timeline_agent(self, test_factory):
        """Factory should create TimelineSpecialistAgent for 'timeline' domain."""
        agent = test_factory.create("timeline")
        
        assert isinstance(agent, TimelineSpecialistAgent)
        assert agent.domain == "timeline"

    def test_create_requirements_agent(self, test_factory):
        """Factory should create RequirementsSpecialistAgent for 'requirements' domain."""
        agent = test_factory.create("requirements")
        
        assert isinstance(agent, RequirementsSpecialistAgent)
        assert agent.domain == "requirements"

    def test_create_general_agent(self, test_factory):
        """Factory should create GeneralSpecialistAgent for 'general' domain."""
        agent = test_factory.create("general")
        
        assert isinstance(agent, GeneralSpecialistAgent)
        assert agent.domain == "general"


class TestAgentFactoryErrorHandling:
    """Tests for AgentFactory error handling."""

    def test_create_unknown_domain_raises_value_error(self, test_factory):
        """Factory should raise ValueError for unknown domains."""
        with pytest.raises(ValueError) as exc_info:
            test_factory.create("unknown_domain")
        
        assert "Unknown domain" in str(exc_info.value)
        assert "unknown_domain" in str(exc_info.value)

    def test_create_empty_domain_raises_value_error(self, test_factory):
        """Factory should raise ValueError for empty domain string."""
        with pytest.raises(ValueError):
            test_factory.create("")


class TestAgentFactoryRegistry:
    """Tests for AgentFactory registry management."""

    def test_get_migrated_domains_returns_all_domains(self, test_factory):
        """Registry should contain all 6 migrated domains."""
        domains = test_factory.get_migrated_domains()
        
        expected = {"financial", "legal", "technical", "timeline", "requirements", "general"}
        assert set(domains) == expected

    def test_is_migrated_returns_true_for_known_domains(self, test_factory):
        """is_migrated should return True for registered domains."""
        assert test_factory.is_migrated("financial") is True
        assert test_factory.is_migrated("legal") is True
        assert test_factory.is_migrated("general") is True

    def test_is_migrated_returns_false_for_unknown_domains(self, test_factory):
        """is_migrated should return False for unregistered domains."""
        assert test_factory.is_migrated("unknown") is False
        assert test_factory.is_migrated("quantitative") is False


class TestAgentFactoryDependencyInjection:
    """Tests for dependency injection in created agents."""

    def test_created_agent_has_injected_llm(self, test_factory, mock_llm):
        """Created agent should have the factory's LLM injected."""
        agent = test_factory.create("financial")
        
        # The agent should have the mock LLM
        assert agent._llm is mock_llm

    def test_multiple_agents_share_same_llm(self, test_factory):
        """All agents from same factory should share the same LLM instance."""
        agent1 = test_factory.create("financial")
        agent2 = test_factory.create("legal")
        agent3 = test_factory.create("technical")
        
        assert agent1._llm is agent2._llm
        assert agent2._llm is agent3._llm
