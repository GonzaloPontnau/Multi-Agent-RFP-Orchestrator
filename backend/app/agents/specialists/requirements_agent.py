"""
Requirements Specialist Agent.

Handles eligibility analysis, gap analysis, qualification criteria,
and compliance verification in RFP documents.
"""

from typing import List

from langchain_core.documents import Document

from app.agents.base import BaseSpecialistAgent
from app.agents.prompts import REQUIREMENTS_PROMPT


class RequirementsSpecialistAgent(BaseSpecialistAgent):
    """Specialist agent for eligibility and requirements analysis."""

    DOMAIN: str = "requirements"
    SYSTEM_PROMPT: str = REQUIREMENTS_PROMPT

    async def generate(self, question: str, context: List[Document]) -> str:
        return await self._default_generate(question, context)
