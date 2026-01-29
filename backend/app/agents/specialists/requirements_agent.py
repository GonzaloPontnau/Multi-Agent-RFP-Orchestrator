"""
Requirements Specialist Agent.

This module implements the specialist agent for eligibility and requirements
analysis in RFP documents. It handles gap analysis, qualification criteria,
and compliance verification.

Example:
    from app.agents.specialists import RequirementsSpecialistAgent
    
    agent = RequirementsSpecialistAgent(llm=llm_service, logger=agent_logger)
    response = await agent.generate(question, context_docs)
"""

from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base import BaseSpecialistAgent, LLMProtocol, LoggerProtocol
from app.agents.prompts import REQUIREMENTS_PROMPT, RESPONSE_FORMAT_TEMPLATE
from app.core.exceptions import AgentProcessingError


class RequirementsSpecialistAgent(BaseSpecialistAgent):
    """
    Specialist agent for eligibility and requirements analysis.
    
    Handles questions related to:
    - Legal capacity (bidder types, consortiums, local participation %)
    - Technical capacity (general/specific experience, required projects)
    - Key personnel required (roles, certifications, years of experience)
    - Financial capacity (equity, liquidity, minimum billing)
    - Disqualifications and restrictions

    Note:
        This agent performs strict gap analysis with numerical comparisons
        and provides COMPLY/NOT COMPLY verdicts for each requirement.
    """

    DOMAIN: str = "requirements"
    SYSTEM_PROMPT: str = REQUIREMENTS_PROMPT

    def __init__(
        self,
        llm: LLMProtocol,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the Requirements Specialist Agent."""
        super().__init__(llm=llm, logger=logger)

    async def generate(
        self,
        question: str,
        context: List[Document],
    ) -> str:
        """
        Generate a requirements analysis response for the given question.

        When company data is provided, performs gap analysis with
        numerical comparisons and verdicts for each requirement.

        Args:
            question: The user's requirements-related question.
            context: List of relevant document chunks for context.

        Returns:
            A formatted response with requirements analysis, including
            gap calculations and compliance verdicts.

        Raises:
            AgentProcessingError: If the LLM invocation fails.
        """
        self._log_enter({"question": question, "context_size": len(context)})

        try:
            context_text = self._format_context(context)

            if not context_text.strip():
                self._log_exit("No requirements context available")
                return "No encontré información de requisitos o elegibilidad relevante para responder tu pregunta."

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
                message="Failed to generate requirements response",
                agent_name=self.node_name,
                original_error=e,
            )
