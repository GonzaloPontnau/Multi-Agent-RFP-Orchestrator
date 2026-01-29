"""
Agent Factory for creating specialist agents.

This module implements the Factory pattern for instantiating specialist agents
based on domain. It provides a centralized registration mechanism and handles
the dependency injection of LLM and logger services.

The factory pattern enables:
- Centralized agent creation logic
- Easy registration of new agent types
- Consistent dependency injection across all agents
- Clear migration path from legacy functions to OOP

Example:
    from app.agents.agent_factory import AgentFactory
    
    factory = AgentFactory(llm=llm_service, logger=agent_logger)
    agent = factory.create("financial")
    response = await agent.generate(question, context)
"""

from typing import Dict, Optional, Type

from app.agents.base import BaseSpecialistAgent, LLMProtocol, LoggerProtocol
from app.agents.prompts import DomainType, AVAILABLE_DOMAINS


class AgentFactory:
    """
    Factory for creating specialist agents by domain.
    
    This factory maintains a registry of domain-to-agent mappings and
    instantiates the appropriate agent class with injected dependencies.

    The factory supports both:
    - Instance-level creation with pre-configured LLM/logger
    - Class-level registration for extending with new agent types

    Attributes:
        _registry: Class-level mapping of domain names to agent classes.

    Example:
        >>> factory = AgentFactory(llm=my_llm, logger=my_logger)
        >>> financial_agent = factory.create("financial")
        >>> response = await financial_agent.generate(question, docs)
    """

    # Class-level registry of domain -> agent class mappings
    # Import inside methods to avoid circular imports
    _registry: Dict[str, Type[BaseSpecialistAgent]] = {}
    _initialized: bool = False

    def __init__(
        self,
        llm: LLMProtocol,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """
        Initialize the agent factory with dependencies.

        Args:
            llm: LLM service implementing LLMProtocol for agent generation.
            logger: Optional logger implementing LoggerProtocol for tracing.
        """
        self._llm = llm
        self._logger = logger
        
        # Initialize registry on first instantiation
        if not AgentFactory._initialized:
            self._initialize_registry()

    @classmethod
    def _initialize_registry(cls) -> None:
        """
        Initialize the agent registry with available implementations.
        
        This method lazily imports agent classes to avoid circular imports
        and registers them in the class-level registry.
        """
        # Import here to avoid circular imports at module level
        from app.agents.specialists import (
            FinancialSpecialistAgent,
            LegalSpecialistAgent,
            TechnicalSpecialistAgent,
            TimelineSpecialistAgent,
            RequirementsSpecialistAgent,
            GeneralSpecialistAgent,
        )

        cls._registry = {
            "financial": FinancialSpecialistAgent,
            "legal": LegalSpecialistAgent,
            "technical": TechnicalSpecialistAgent,
            "timeline": TimelineSpecialistAgent,
            "requirements": RequirementsSpecialistAgent,
            "general": GeneralSpecialistAgent,
            # Note: "quantitative" is handled by quant_node, not specialist_node
            # If routed here by mistake, falls back to GeneralSpecialistAgent
        }
        cls._initialized = True

    def create(self, domain: str) -> BaseSpecialistAgent:
        """
        Create a specialist agent for the specified domain.

        Args:
            domain: The domain identifier (e.g., 'financial', 'legal').

        Returns:
            An instantiated specialist agent for the domain.

        Raises:
            NotImplementedError: If the domain is not yet migrated to OOP.
            ValueError: If the domain is not a valid domain type.

        Example:
            >>> agent = factory.create("financial")
            >>> isinstance(agent, FinancialSpecialistAgent)
            True
        """
        # Validate domain is known
        if domain not in AVAILABLE_DOMAINS:
            raise ValueError(
                f"Unknown domain: '{domain}'. "
                f"Valid domains are: {AVAILABLE_DOMAINS}"
            )

        # Check if agent class is registered (migrated)
        agent_class = self._registry.get(domain)
        
        if agent_class is None:
            raise NotImplementedError(
                f"Agent for domain '{domain}' has not been migrated to OOP yet. "
                f"Currently migrated domains: {list(self._registry.keys())}. "
                f"Use legacy subagents.specialist_generate() for now."
            )

        # Instantiate with injected dependencies
        return agent_class(llm=self._llm, logger=self._logger)

    @classmethod
    def register(
        cls,
        domain: str,
        agent_class: Type[BaseSpecialistAgent],
    ) -> None:
        """
        Register a new agent class for a domain.

        This method allows dynamic registration of new agent types,
        useful for plugins or testing with mock agents.

        Args:
            domain: The domain identifier to register.
            agent_class: The agent class to instantiate for this domain.

        Raises:
            ValueError: If domain is not in AVAILABLE_DOMAINS.

        Example:
            >>> AgentFactory.register("legal", LegalSpecialistAgent)
        """
        if domain not in AVAILABLE_DOMAINS:
            raise ValueError(
                f"Cannot register unknown domain: '{domain}'. "
                f"Valid domains are: {AVAILABLE_DOMAINS}"
            )
        cls._registry[domain] = agent_class

    @classmethod
    def get_migrated_domains(cls) -> list:
        """
        Get list of domains that have been migrated to OOP.

        Returns:
            List of domain names with registered agent classes.
        """
        return list(cls._registry.keys())

    @classmethod
    def is_migrated(cls, domain: str) -> bool:
        """
        Check if a domain has been migrated to OOP.

        Args:
            domain: The domain identifier to check.

        Returns:
            True if the domain has a registered agent class.
        """
        return domain in cls._registry

    def create_or_fallback(
        self,
        domain: str,
        fallback_fn: Optional[callable] = None,
    ) -> BaseSpecialistAgent:
        """
        Create agent if migrated, otherwise use fallback.

        This method supports gradual migration by allowing legacy
        function calls as fallback for non-migrated domains.

        Args:
            domain: The domain identifier.
            fallback_fn: Optional fallback function for non-migrated domains.

        Returns:
            Specialist agent if migrated.

        Raises:
            NotImplementedError: If not migrated and no fallback provided.
        """
        if self.is_migrated(domain):
            return self.create(domain)
        
        if fallback_fn is not None:
            # Return a wrapper that calls the legacy function
            # This is a bridge pattern for gradual migration
            raise NotImplementedError(
                f"Fallback wrapper not implemented. Domain '{domain}' "
                f"needs migration or explicit fallback handling."
            )
        
        raise NotImplementedError(
            f"Domain '{domain}' not migrated and no fallback provided."
        )
