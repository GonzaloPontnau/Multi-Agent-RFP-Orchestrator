"""
Unit tests for FinancialSpecialistAgent.

Tests the financial specialist agent's generate method with various scenarios.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from langchain_core.documents import Document

from app.agents.specialists import FinancialSpecialistAgent
from app.agents.prompts import FINANCIAL_PROMPT
from app.core.exceptions import AgentProcessingError


class TestFinancialAgentEmptyContext:
    """Tests for FinancialSpecialistAgent with empty context."""

    @pytest.mark.asyncio
    async def test_generate_with_empty_context_returns_default_message(self, mock_llm):
        """Agent should return default message when context is empty."""
        agent = FinancialSpecialistAgent(llm=mock_llm)
        
        result = await agent.generate(
            question="¿Cuál es el presupuesto?",
            context=[],
        )
        
        assert "No encontré información financiera" in result
        # LLM should NOT be called when context is empty
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_with_whitespace_context_returns_default_message(
        self, mock_llm, sample_document
    ):
        """Agent should return default message when context contains only whitespace."""
        agent = FinancialSpecialistAgent(llm=mock_llm)
        
        # Create document with only whitespace content
        empty_doc = Document(page_content="   \n\t  ")
        
        result = await agent.generate(
            question="¿Cuál es el presupuesto?",
            context=[empty_doc],
        )
        
        assert "No encontré información financiera" in result


class TestFinancialAgentWithContext:
    """Tests for FinancialSpecialistAgent with valid context."""

    @pytest.mark.asyncio
    async def test_generate_calls_llm_with_context(self, mock_llm, sample_context):
        """Agent should call LLM when context has content."""
        mock_llm.ainvoke.return_value.content = "El presupuesto total es USD 5,000,000."
        
        agent = FinancialSpecialistAgent(llm=mock_llm)
        
        result = await agent.generate(
            question="¿Cuál es el presupuesto total?",
            context=sample_context,
        )
        
        # LLM should be called
        mock_llm.ainvoke.assert_called_once()
        
        # Result should be LLM's response
        assert result == "El presupuesto total es USD 5,000,000."

    @pytest.mark.asyncio
    async def test_generate_uses_financial_prompt(self, mock_llm, sample_context):
        """Agent should use FINANCIAL_PROMPT in system message."""
        agent = FinancialSpecialistAgent(llm=mock_llm)
        
        await agent.generate(
            question="¿Cuál es el presupuesto?",
            context=sample_context,
        )
        
        # Get the messages passed to LLM
        call_args = mock_llm.ainvoke.call_args[0][0]
        system_message = call_args[0]
        
        # System message should contain financial-specific keywords
        assert "FINANCIEROS" in system_message.content or "ECONÓMICOS" in system_message.content

    @pytest.mark.asyncio
    async def test_generate_includes_question_in_user_message(
        self, mock_llm, sample_context
    ):
        """Agent should include the question in user message."""
        agent = FinancialSpecialistAgent(llm=mock_llm)
        question = "¿Cuáles son los hitos de pago?"
        
        await agent.generate(
            question=question,
            context=sample_context,
        )
        
        # Get the messages passed to LLM
        call_args = mock_llm.ainvoke.call_args[0][0]
        user_message = call_args[1]
        
        # User message should contain the question
        assert question in user_message.content

    @pytest.mark.asyncio
    async def test_generate_includes_context_in_user_message(
        self, mock_llm, sample_context
    ):
        """Agent should include document context in user message."""
        agent = FinancialSpecialistAgent(llm=mock_llm)
        
        await agent.generate(
            question="¿Cuál es el presupuesto?",
            context=sample_context,
        )
        
        # Get the messages passed to LLM
        call_args = mock_llm.ainvoke.call_args[0][0]
        user_message = call_args[1]
        
        # User message should contain content from documents
        assert "USD 5,000,000" in user_message.content
        assert "garantía de cumplimiento" in user_message.content


class TestFinancialAgentErrorHandling:
    """Tests for FinancialSpecialistAgent error handling."""

    @pytest.mark.asyncio
    async def test_generate_raises_agent_error_on_llm_failure(
        self, mock_llm, sample_context
    ):
        """Agent should raise AgentProcessingError when LLM fails."""
        mock_llm.ainvoke.side_effect = Exception("LLM API Error")
        
        agent = FinancialSpecialistAgent(llm=mock_llm)
        
        with pytest.raises(AgentProcessingError) as exc_info:
            await agent.generate(
                question="¿Cuál es el presupuesto?",
                context=sample_context,
            )
        
        assert "Failed to generate financial response" in str(exc_info.value)
        assert "specialist_financial" in str(exc_info.value)


class TestFinancialAgentProperties:
    """Tests for FinancialSpecialistAgent properties."""

    def test_domain_property(self, mock_llm):
        """Agent should have correct domain property."""
        agent = FinancialSpecialistAgent(llm=mock_llm)
        assert agent.domain == "financial"

    def test_node_name_property(self, mock_llm):
        """Agent should have correct node_name for logging."""
        agent = FinancialSpecialistAgent(llm=mock_llm)
        assert agent.node_name == "specialist_financial"

    def test_system_prompt_contains_financial_keywords(self, mock_llm):
        """Agent's system prompt should contain financial domain keywords."""
        agent = FinancialSpecialistAgent(llm=mock_llm)
        prompt = agent.SYSTEM_PROMPT
        
        assert "Presupuesto" in prompt or "presupuesto" in prompt.lower()
        assert "garantía" in prompt.lower() or "financiamiento" in prompt.lower()


class TestFinancialAgentWithLogger:
    """Tests for FinancialSpecialistAgent logging behavior."""

    @pytest.mark.asyncio
    async def test_generate_logs_entry_and_exit(
        self, mock_llm, mock_logger, sample_context
    ):
        """Agent should log node entry and exit."""
        agent = FinancialSpecialistAgent(llm=mock_llm, logger=mock_logger)
        
        await agent.generate(
            question="¿Cuál es el presupuesto?",
            context=sample_context,
        )
        
        # Should log entry
        mock_logger.node_enter.assert_called()
        # Should log exit
        mock_logger.node_exit.assert_called()

    @pytest.mark.asyncio
    async def test_generate_logs_error_on_failure(
        self, mock_llm, mock_logger, sample_context
    ):
        """Agent should log errors when generation fails."""
        mock_llm.ainvoke.side_effect = Exception("Test error")
        
        agent = FinancialSpecialistAgent(llm=mock_llm, logger=mock_logger)
        
        with pytest.raises(AgentProcessingError):
            await agent.generate(
                question="¿Cuál es el presupuesto?",
                context=sample_context,
            )
        
        # Should log the error
        mock_logger.error.assert_called()
