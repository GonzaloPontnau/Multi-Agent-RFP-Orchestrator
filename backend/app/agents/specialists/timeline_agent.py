"""
Timeline Specialist Agent.

This module implements the specialist agent for timeline and schedule
questions in RFP documents. It handles procurement schedules, contract
duration, milestones, deadlines, and warranty periods.

Example:
    from app.agents.specialists import TimelineSpecialistAgent
    
    agent = TimelineSpecialistAgent(llm=llm_service, logger=agent_logger)
    response = await agent.generate(question, context_docs)
"""

from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base import BaseSpecialistAgent, LLMProtocol, LoggerProtocol
from app.agents.prompts import TIMELINE_PROMPT, RESPONSE_FORMAT_TEMPLATE
from app.core.exceptions import AgentProcessingError


class TimelineSpecialistAgent(BaseSpecialistAgent):
    """
    Specialist agent for schedules and timelines in RFPs.
    
    Handles questions related to:
    - Procurement process schedule (publication, queries, opening, award)
    - Contract duration and implementation phases
    - Milestones with specific dates
    - Delivery deadlines and milestones
    - Warranty and maintenance periods

    Note:
        This agent has strict instructions to present dates in tables
        and to never invent dates not present in the context.
    """

    DOMAIN: str = "timeline"
    SYSTEM_PROMPT: str = TIMELINE_PROMPT

    def __init__(
        self,
        llm: LLMProtocol,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the Timeline Specialist Agent."""
        super().__init__(llm=llm, logger=logger)

    async def generate(
        self,
        question: str,
        context: List[Document],
    ) -> str:
        """
        Generate a timeline analysis response for the given question.

        The response will present dates in chronological tables when found,
        and explicitly state when specific dates are not available.

        Args:
            question: The user's timeline-related question.
            context: List of relevant document chunks for context.

        Returns:
            A formatted response with timeline analysis, including
            chronological tables and calculated durations.

        Raises:
            AgentProcessingError: If the LLM invocation fails.
        """
        self._log_enter({"question": question, "context_size": len(context)})

        try:
            context_text = self._format_context(context)

            if not context_text.strip():
                self._log_exit("No timeline context available")
                return "No encontré información de cronograma o plazos relevante para responder tu pregunta."

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
                message="Failed to generate timeline response",
                agent_name=self.node_name,
                original_error=e,
            )
