"""
General Specialist Agent.

This module implements the general-purpose specialist agent that handles
questions spanning multiple domains or those that don't fit a specific
specialization.

Example:
    from app.agents.specialists import GeneralSpecialistAgent
    
    agent = GeneralSpecialistAgent(llm=llm_service, logger=agent_logger)
    response = await agent.generate(question, context_docs)
"""

from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base import BaseSpecialistAgent, LLMProtocol, LoggerProtocol
from app.agents.prompts import GENERAL_PROMPT, RESPONSE_FORMAT_TEMPLATE
from app.core.exceptions import AgentProcessingError


class GeneralSpecialistAgent(BaseSpecialistAgent):
    """
    General-purpose specialist agent for comprehensive RFP analysis.
    
    Handles questions that:
    - Span multiple domains (legal + technical + financial)
    - Don't clearly fit a specific specialization
    - Require a broad overview of the document

    This agent provides comprehensive responses covering all
    relevant aspects when the question is too broad for
    domain-specific specialists.
    """

    DOMAIN: str = "general"
    SYSTEM_PROMPT: str = GENERAL_PROMPT

    def __init__(
        self,
        llm: LLMProtocol,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the General Specialist Agent."""
        super().__init__(llm=llm, logger=logger)

    async def generate(
        self,
        question: str,
        context: List[Document],
    ) -> str:
        """
        Generate a comprehensive response for the given question.

        Provides broad analysis covering all relevant aspects
        of the question across multiple domains.

        Args:
            question: The user's question.
            context: List of relevant document chunks for context.

        Returns:
            A formatted response with comprehensive analysis
            organized by relevant sections.

        Raises:
            AgentProcessingError: If the LLM invocation fails.
        """
        self._log_enter({"question": question, "context_size": len(context)})

        try:
            context_text = self._format_context(context)

            if not context_text.strip():
                self._log_exit("No context available")
                return "No encontré información relevante para responder tu pregunta."

            self._log_debug(f"Processing with {len(context)} documents")

            full_system_prompt = f"{self.SYSTEM_PROMPT}\n\n{RESPONSE_FORMAT_TEMPLATE}"

            messages = [
                SystemMessage(content=full_system_prompt),
                HumanMessage(
                    content=f"Contexto del documento:\n{context_text}\n\nPregunta: {question}"
                ),
            ]

            response = await self._llm.ainvoke(messages)
            answer = response.content

            self._log_exit(f"Generated {len(answer)} chars")
            return answer

        except Exception as e:
            self._log_error(e)
            raise AgentProcessingError(
                message="Failed to generate response",
                agent_name=self.node_name,
                original_error=e,
            )
