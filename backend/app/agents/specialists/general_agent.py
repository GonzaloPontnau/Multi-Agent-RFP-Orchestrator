"""
General Specialist Agent.

Handles questions spanning multiple domains or those that
don't fit a specific specialization in RFP documents.
"""

from typing import List

from langchain_core.documents import Document

from app.agents.base import BaseSpecialistAgent
from app.agents.prompts import GENERAL_PROMPT


class GeneralSpecialistAgent(BaseSpecialistAgent):
    """General-purpose specialist agent for comprehensive RFP analysis."""

    DOMAIN: str = "general"
    SYSTEM_PROMPT: str = GENERAL_PROMPT

    async def generate(self, question: str, context: List[Document]) -> str:
        return await self._default_generate(question, context)
