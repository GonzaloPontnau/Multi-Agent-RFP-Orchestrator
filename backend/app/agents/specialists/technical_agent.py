"""
Technical Specialist Agent.

This module implements the specialist agent for technical domain questions
in RFP documents. It handles architecture, technology stack, integrations,
infrastructure, security, and SLA requirements.

Example:
    from app.agents.specialists import TechnicalSpecialistAgent
    
    agent = TechnicalSpecialistAgent(llm=llm_service, logger=agent_logger)
    response = await agent.generate(question, context_docs)
"""

from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base import BaseSpecialistAgent, LLMProtocol, LoggerProtocol
from app.agents.prompts import TECHNICAL_PROMPT, RESPONSE_FORMAT_TEMPLATE
from app.core.exceptions import AgentProcessingError


class TechnicalSpecialistAgent(BaseSpecialistAgent):
    """
    Specialist agent for technical and architecture aspects of RFPs.
    
    Handles questions related to:
    - Solution architecture and technical principles
    - Technology stack (languages, frameworks, databases)
    - System integrations (APIs, protocols, legacy systems)
    - Infrastructure (data centers, cloud, networking)
    - Technical security (WAF, encryption, ISO certifications)
    - Functional modules and technical requirements
    - Performance and availability SLAs
    """

    DOMAIN: str = "technical"
    SYSTEM_PROMPT: str = TECHNICAL_PROMPT

    def __init__(
        self,
        llm: LLMProtocol,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the Technical Specialist Agent."""
        super().__init__(llm=llm, logger=logger)

    async def generate(
        self,
        question: str,
        context: List[Document],
    ) -> str:
        """
        Generate a technical analysis response for the given question.

        Args:
            question: The user's technical-related question.
            context: List of relevant document chunks for context.

        Returns:
            A formatted response with technical analysis, including
            versions, standards, certifications, and metrics.

        Raises:
            AgentProcessingError: If the LLM invocation fails.
        """
        self._log_enter({"question": question, "context_size": len(context)})

        try:
            context_text = self._format_context(context)

            if not context_text.strip():
                self._log_exit("No technical context available")
                return "No encontré información técnica relevante para responder tu pregunta."

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
                message="Failed to generate technical response",
                agent_name=self.node_name,
                original_error=e,
            )
