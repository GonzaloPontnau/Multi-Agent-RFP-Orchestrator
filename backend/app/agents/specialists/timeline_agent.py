"""
Timeline Specialist Agent.

Handles procurement schedules, contract duration, milestones,
deadlines, and warranty periods in RFP documents.
"""

from typing import List

from langchain_core.documents import Document

from app.agents.base import BaseSpecialistAgent
from app.agents.prompts import TIMELINE_PROMPT


class TimelineSpecialistAgent(BaseSpecialistAgent):
    """Specialist agent for schedules and timelines in RFPs."""

    DOMAIN: str = "timeline"
    SYSTEM_PROMPT: str = TIMELINE_PROMPT

    async def generate(self, question: str, context: List[Document]) -> str:
        return await self._default_generate(question, context)
