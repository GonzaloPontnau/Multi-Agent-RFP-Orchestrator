"""
Legal Specialist Agent.

Handles legal frameworks, regulations, jurisdiction,
IP rights, and contractual obligations in RFP documents.
"""

from typing import List

from langchain_core.documents import Document

from app.agents.base import BaseSpecialistAgent
from app.agents.prompts import LEGAL_PROMPT


class LegalSpecialistAgent(BaseSpecialistAgent):
    """Specialist agent for legal and regulatory aspects of RFPs."""

    DOMAIN: str = "legal"
    SYSTEM_PROMPT: str = LEGAL_PROMPT

    async def generate(self, question: str, context: List[Document]) -> str:
        return await self._default_generate(question, context)
