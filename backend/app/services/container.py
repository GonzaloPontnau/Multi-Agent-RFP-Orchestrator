"""
Dependency Injection Container.

This module provides a centralized container for managing service dependencies
across the application. It ensures singletons for expensive resources like
LLM connections and provides easy access to factories.

The container pattern enables:
- Centralized dependency management
- Easy testing with mock dependencies
- Lazy initialization of expensive resources
- Consistent lifecycle management

Example:
    from app.services.container import get_container
    
    container = get_container()
    factory = container.agent_factory
    agent = factory.create("financial")
"""

from functools import lru_cache
from typing import Optional

from app.core.logging import AgentLogger
from app.services.llm_factory import get_llm


class DependencyContainer:
    """
    Centralized container for application dependencies.
    
    This container holds references to shared services and factories,
    providing lazy initialization and singleton behavior for expensive
    resources.

    Attributes:
        _llm: Cached LLM service instance.
        _agent_factory: Cached AgentFactory instance.
        _logger: Logger instance for agent tracing.
    """

    def __init__(self) -> None:
        """Initialize the container with lazy service references."""
        self._llm = None
        self._agent_factory = None
        self._logger: Optional[AgentLogger] = None

    @property
    def llm(self):
        """
        Get the LLM service instance.
        
        Returns:
            LLM service for text generation.
        """
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    @property
    def logger(self) -> AgentLogger:
        """
        Get the agent logger instance.
        
        Returns:
            AgentLogger for tracing agent operations.
        """
        if self._logger is None:
            self._logger = AgentLogger("container")
        return self._logger

    @property
    def agent_factory(self):
        """
        Get the AgentFactory instance.
        
        The factory is initialized with the container's LLM and logger,
        enabling dependency injection into all created agents.
        
        Returns:
            AgentFactory for creating specialist agents.
        """
        if self._agent_factory is None:
            # Import here to avoid circular imports
            from app.agents.agent_factory import AgentFactory
            self._agent_factory = AgentFactory(
                llm=self.llm,
                logger=self.logger,
            )
        return self._agent_factory

    def reset(self) -> None:
        """
        Reset all cached services.
        
        Useful for testing to ensure fresh instances.
        """
        self._llm = None
        self._agent_factory = None
        self._logger = None

    def override_llm(self, mock_llm) -> None:
        """
        Override the LLM service with a mock.
        
        Args:
            mock_llm: Mock LLM implementation for testing.
        """
        self._llm = mock_llm
        # Reset factory to pick up new LLM
        self._agent_factory = None


@lru_cache(maxsize=1)
def get_container() -> DependencyContainer:
    """
    Get the singleton DependencyContainer instance.
    
    Uses lru_cache to ensure only one container exists per process.
    
    Returns:
        The global DependencyContainer instance.
        
    Example:
        >>> container = get_container()
        >>> agent = container.agent_factory.create("financial")
    """
    return DependencyContainer()


def reset_container() -> None:
    """
    Reset the global container singleton.
    
    Clears the lru_cache and allows a fresh container to be created.
    Useful for testing isolation.
    """
    get_container.cache_clear()
