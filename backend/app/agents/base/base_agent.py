"""
Abstract base class for specialist agents.

This module defines the foundation for all domain-specific specialist agents
in the RFP Orchestrator. It uses dependency injection for the LLM service
and provides common functionality for context formatting and message building.

The design follows these principles:
- Open/Closed Principle: Extend via inheritance, not modification
- Dependency Injection: LLM is injected, enabling easy testing with mocks
- Template Method Pattern: Subclasses implement `generate()`, base handles common logic

Example:
    class LegalSpecialistAgent(BaseSpecialistAgent):
        DOMAIN = "legal"
        
        async def generate(self, question: str, context: list[Document]) -> str:
            # Custom generation logic
            ...
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Protocol, runtime_checkable

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.prompts import get_full_prompt, RESPONSE_FORMAT_TEMPLATE


# =============================================================================
# PROTOCOLS (For Dependency Injection)
# =============================================================================


@runtime_checkable
class LLMProtocol(Protocol):
    """
    Protocol defining the interface for LLM services.
    
    This allows dependency injection of any LLM implementation
    that satisfies this interface, including mocks for testing.
    
    The protocol is runtime_checkable to enable isinstance() checks.
    """

    async def ainvoke(self, messages: List[BaseMessage]) -> Any:
        """
        Asynchronously invoke the LLM with a list of messages.

        Args:
            messages: List of messages (SystemMessage, HumanMessage, etc.)

        Returns:
            LLM response object with a `content` attribute.
        """
        ...


@runtime_checkable
class LoggerProtocol(Protocol):
    """
    Protocol defining the interface for agent loggers.
    
    Allows injection of custom loggers for different environments.
    """

    def node_enter(self, node_name: str, state: dict) -> None:
        """Log entry into a node."""
        ...

    def node_exit(self, node_name: str, message: str) -> None:
        """Log exit from a node."""
        ...

    def debug(self, node_name: str, message: str) -> None:
        """Log debug message."""
        ...

    def error(self, node_name: str, error: Exception) -> None:
        """Log error."""
        ...


# =============================================================================
# BASE AGENT CLASS
# =============================================================================


class BaseSpecialistAgent(ABC):
    """
    Abstract base class for domain-specific specialist agents.
    
    Each specialist agent handles questions for a specific domain
    (legal, technical, financial, etc.) using domain-specific prompts
    and generation strategies.

    Attributes:
        DOMAIN: The domain this specialist handles (override in subclass).
        SYSTEM_PROMPT: The system prompt for this specialist (override in subclass).

    Class Design:
        - Uses dependency injection for LLM and Logger
        - Provides common helper methods for context formatting
        - Defines abstract `generate()` method for subclasses to implement
    """

    # Override these in subclasses
    DOMAIN: str = "general"
    SYSTEM_PROMPT: str = ""

    def __init__(
        self,
        llm: LLMProtocol,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """
        Initialize the specialist agent.

        Args:
            llm: LLM service implementing LLMProtocol.
            logger: Optional logger implementing LoggerProtocol.
        """
        self._llm = llm
        self._logger = logger

    @property
    def domain(self) -> str:
        """Return the domain this specialist handles."""
        return self.DOMAIN

    @property
    def node_name(self) -> str:
        """Return the node name for logging purposes."""
        return f"specialist_{self.DOMAIN}"

    # -------------------------------------------------------------------------
    # Abstract Methods (Must be implemented by subclasses)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def generate(
        self,
        question: str,
        context: List[Document],
    ) -> str:
        """
        Generate a response for the given question using the context.

        This is the main method that subclasses must implement.
        It should use the specialist's domain-specific logic to
        produce an appropriate response.

        Args:
            question: The user's question.
            context: List of relevant documents for context.

        Returns:
            The generated response string.

        Raises:
            AgentProcessingError: If generation fails.
        """
        pass

    # -------------------------------------------------------------------------
    # Concrete Helper Methods
    # -------------------------------------------------------------------------

    def _format_context(
        self,
        context: List[Document],
        separator: str = "\n\n---\n\n",
        max_length: Optional[int] = None,
    ) -> str:
        """
        Format a list of documents into a single context string.

        Args:
            context: List of documents to format.
            separator: String to use between document contents.
            max_length: Optional maximum length for the result.

        Returns:
            Formatted context string ready for inclusion in prompts.

        Example:
            >>> docs = [Document(page_content="A"), Document(page_content="B")]
            >>> agent._format_context(docs)
            'A\\n\\n---\\n\\nB'
        """
        if not context:
            return ""

        formatted = separator.join(doc.page_content for doc in context)

        if max_length and len(formatted) > max_length:
            formatted = formatted[:max_length] + "\n\n[Contexto truncado...]"

        return formatted

    def _build_messages(
        self,
        question: str,
        context_text: str,
        system_prompt: Optional[str] = None,
        include_response_format: bool = True,
    ) -> List[BaseMessage]:
        """
        Build the message list for LLM invocation.

        Constructs a list of messages with the system prompt and user question,
        following the chat format expected by LangChain.

        Args:
            question: The user's question.
            context_text: Pre-formatted context string.
            system_prompt: Override for the default system prompt.
            include_response_format: Whether to append response format guidelines.

        Returns:
            List of messages ready for LLM invocation.

        Example:
            >>> messages = agent._build_messages("What is X?", context)
            >>> response = await llm.ainvoke(messages)
        """
        # Use provided prompt or get from prompts module
        if system_prompt:
            full_system = system_prompt
            if include_response_format:
                full_system = f"{system_prompt}\n\n{RESPONSE_FORMAT_TEMPLATE}"
        else:
            full_system = get_full_prompt(self.DOMAIN, include_response_format)

        user_content = (
            f"Contexto del documento:\n{context_text}\n\n"
            f"Pregunta: {question}"
        )

        return [
            SystemMessage(content=full_system),
            HumanMessage(content=user_content),
        ]

    def _log_enter(self, state: Optional[dict] = None) -> None:
        """Log entry into the specialist node."""
        if self._logger:
            self._logger.node_enter(self.node_name, state or {})

    def _log_exit(self, message: str) -> None:
        """Log exit from the specialist node."""
        if self._logger:
            self._logger.node_exit(self.node_name, message)

    def _log_debug(self, message: str) -> None:
        """Log debug message."""
        if self._logger:
            self._logger.debug(self.node_name, message)

    def _log_error(self, error: Exception) -> None:
        """Log error."""
        if self._logger:
            self._logger.error(self.node_name, error)

    # -------------------------------------------------------------------------
    # Default Generate Implementation (Optional override)
    # -------------------------------------------------------------------------

    async def _default_generate(
        self,
        question: str,
        context: List[Document],
    ) -> str:
        """
        Default implementation of generate logic.

        Subclasses can call this method or override completely.
        This provides a standard flow: format context, build messages, invoke LLM.

        Args:
            question: The user's question.
            context: List of relevant documents for context.

        Returns:
            The generated response string.
        """
        self._log_enter({"question": question})

        context_text = self._format_context(context)

        if not context_text.strip():
            self._log_exit("No context available")
            return "No encontré información relevante para responder tu pregunta."

        self._log_debug(f"Using {len(context)} docs for generation")

        messages = self._build_messages(question, context_text)
        response = await self._llm.ainvoke(messages)
        answer = response.content

        self._log_exit(f"{len(answer)} chars generated")
        return answer
