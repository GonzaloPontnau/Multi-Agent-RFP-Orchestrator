"""
Legal Specialist Agent.

This module implements the specialist agent for legal domain questions
in RFP documents. It handles legal frameworks, regulations, jurisdiction,
IP rights, and contractual obligations.

Example:
    from app.agents.specialists import LegalSpecialistAgent
    
    agent = LegalSpecialistAgent(llm=llm_service, logger=agent_logger)
    response = await agent.generate(question, context_docs)
"""

from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base import BaseSpecialistAgent, LLMProtocol, LoggerProtocol
from app.agents.prompts import LEGAL_PROMPT, RESPONSE_FORMAT_TEMPLATE
from app.core.exceptions import AgentProcessingError


class LegalSpecialistAgent(BaseSpecialistAgent):
    """
    Specialist agent for legal and regulatory aspects of RFPs.
    
    Handles questions related to:
    - Legal and regulatory framework (laws, decrees, resolutions)
    - Jurisdiction and dispute resolution
    - Intellectual property and software licensing
    - Confidentiality and data protection (Law 25.326, GDPR)
    - Contractual sanctions (termination, disqualification, legal fines)
    - Obligations and responsibilities of parties

    Note:
        SLAs (availability, uptime, latency) are TECHNICAL topics, not legal.
    """

    DOMAIN: str = "legal"
    SYSTEM_PROMPT: str = LEGAL_PROMPT

    def __init__(
        self,
        llm: LLMProtocol,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the Legal Specialist Agent."""
        super().__init__(llm=llm, logger=logger)

    async def generate(
        self,
        question: str,
        context: List[Document],
    ) -> str:
        """
        Generate a legal analysis response for the given question.

        Args:
            question: The user's legal-related question.
            context: List of relevant document chunks for context.

        Returns:
            A formatted response with legal analysis, including
            article citations, laws, and regulatory references.

        Raises:
            AgentProcessingError: If the LLM invocation fails.
        """
        self._log_enter({"question": question, "context_size": len(context)})

        try:
            context_text = self._format_context(context)

            if not context_text.strip():
                self._log_exit("No legal context available")
                return "No encontré información legal relevante para responder tu pregunta."

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
                message="Failed to generate legal response",
                agent_name=self.node_name,
                original_error=e,
            )
