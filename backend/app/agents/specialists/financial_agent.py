"""
Financial Specialist Agent.

This module implements the concrete specialist agent for financial domain
questions in RFP documents. It handles budget, payment schemes, guarantees,
and financial capacity requirements.

Example:
    from app.agents.specialists import FinancialSpecialistAgent
    
    agent = FinancialSpecialistAgent(llm=llm_service, logger=agent_logger)
    response = await agent.generate(question, context_docs)
"""

from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base import BaseSpecialistAgent, LLMProtocol, LoggerProtocol
from app.agents.prompts import FINANCIAL_PROMPT, RESPONSE_FORMAT_TEMPLATE
from app.core.exceptions import AgentProcessingError


class FinancialSpecialistAgent(BaseSpecialistAgent):
    """
    Specialist agent for financial and economic aspects of RFPs.
    
    Handles questions related to:
    - Official budget and component breakdown
    - Funding sources
    - Payment schemes and milestones
    - Required guarantees (bid maintenance, performance, advance)
    - Price adjustment mechanisms
    - Financial capacity requirements (equity, liquidity, billing)

    Attributes:
        DOMAIN: The domain identifier ("financial").
        SYSTEM_PROMPT: The specialized prompt for financial analysis.
    """

    DOMAIN: str = "financial"
    SYSTEM_PROMPT: str = FINANCIAL_PROMPT

    def __init__(
        self,
        llm: LLMProtocol,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """
        Initialize the Financial Specialist Agent.

        Args:
            llm: LLM service implementing LLMProtocol for generation.
            logger: Optional logger implementing LoggerProtocol for tracing.
        """
        super().__init__(llm=llm, logger=logger)

    async def generate(
        self,
        question: str,
        context: List[Document],
    ) -> str:
        """
        Generate a financial analysis response for the given question.

        This method processes the question using the financial specialist's
        expertise in budgets, payments, guarantees, and financial requirements.

        Args:
            question: The user's financial-related question.
            context: List of relevant document chunks for context.

        Returns:
            A formatted response with financial analysis, including
            amounts, percentages, and specific citations from documents.

        Raises:
            AgentProcessingError: If the LLM invocation fails.

        Example:
            >>> response = await agent.generate(
            ...     "¿Cuál es el presupuesto total?",
            ...     context_docs
            ... )
        """
        self._log_enter({"question": question, "context_size": len(context)})

        try:
            # Format context from documents
            context_text = self._format_context(context)

            # Handle empty context case
            if not context_text.strip():
                self._log_exit("No financial context available")
                return "No encontré información financiera relevante para responder tu pregunta."

            self._log_debug(f"Processing with {len(context)} documents")

            # Build the full system prompt with response format
            full_system_prompt = f"{self.SYSTEM_PROMPT}\n\n{RESPONSE_FORMAT_TEMPLATE}"

            # Construct messages for LLM
            messages = [
                SystemMessage(content=full_system_prompt),
                HumanMessage(
                    content=f"Contexto del documento:\n{context_text}\n\nPregunta: {question}"
                ),
            ]

            # Invoke LLM
            response = await self._llm.ainvoke(messages)
            answer = response.content

            self._log_exit(f"Generated {len(answer)} chars")
            return answer

        except Exception as e:
            self._log_error(e)
            raise AgentProcessingError(
                message="Failed to generate financial response",
                agent_name=self.node_name,
                original_error=e,
            )
