"""
Pytest configuration and shared fixtures.

This module provides common fixtures for testing TenderCortex.
All fixtures use mocks to avoid real API calls to LLM or vector store services.

Usage:
    def test_example(mock_llm, test_container):
        # mock_llm is already configured as AsyncMock
        # test_container has mocked dependencies
        pass
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# LLM MOCK FIXTURES
# =============================================================================


@pytest.fixture
def mock_llm_response():
    """
    Factory fixture for creating mock LLM responses.
    
    Returns a factory function that creates response objects with
    custom content.
    
    Usage:
        def test_example(mock_llm_response):
            response = mock_llm_response("Test content")
            assert response.content == "Test content"
    """
    def _create_response(content: str = "Mocked LLM response"):
        response = MagicMock()
        response.content = content
        return response
    return _create_response


@pytest.fixture
def mock_llm(mock_llm_response):
    """
    AsyncMock that simulates LLM behavior.
    
    The mock is pre-configured to return a default response.
    Override in individual tests as needed.
    
    Usage:
        async def test_example(mock_llm):
            # Default response
            result = await mock_llm.ainvoke([])
            assert result.content == "Mocked LLM response"
            
            # Custom response
            mock_llm.ainvoke.return_value.content = "Custom"
            result = await mock_llm.ainvoke([])
            assert result.content == "Custom"
    """
    llm = AsyncMock()
    llm.ainvoke.return_value = mock_llm_response("Mocked LLM response")
    return llm


# =============================================================================
# RAG SERVICE MOCK FIXTURES
# =============================================================================


@pytest.fixture
def mock_rag_service():
    """
    AsyncMock that simulates RAG service behavior.
    
    Usage:
        async def test_example(mock_rag_service):
            mock_rag_service.retrieve.return_value = [doc1, doc2]
    """
    rag = AsyncMock()
    rag.retrieve.return_value = []
    rag.ingest.return_value = True
    return rag


# =============================================================================
# DOCUMENT FIXTURES
# =============================================================================


@pytest.fixture
def sample_document():
    """
    Factory fixture for creating sample LangChain Documents.
    
    Usage:
        def test_example(sample_document):
            doc = sample_document("Content here", source="test.pdf")
    """
    from langchain_core.documents import Document
    
    def _create_document(
        content: str = "Sample document content",
        source: str = "test_document.pdf",
        page: int = 1,
    ):
        return Document(
            page_content=content,
            metadata={"source": source, "page": page},
        )
    return _create_document


@pytest.fixture
def sample_context(sample_document):
    """
    Pre-built list of sample documents for context.
    
    Usage:
        def test_example(sample_context):
            assert len(sample_context) == 3
    """
    return [
        sample_document("El presupuesto total es de USD 5,000,000.", page=1),
        sample_document("La garantía de cumplimiento será del 10%.", page=2),
        sample_document("Forma de pago: 30% anticipo, 70% contra entrega.", page=3),
    ]


# =============================================================================
# CONTAINER FIXTURES
# =============================================================================


@pytest.fixture
def test_container(mock_llm):
    """
    DependencyContainer with mocked LLM for isolated testing.
    
    This fixture creates a fresh container and overrides the LLM
    with a mock, enabling unit testing without real API calls.
    
    Usage:
        def test_example(test_container):
            factory = test_container.agent_factory
            agent = factory.create("financial")
    """
    from app.services.container import DependencyContainer
    
    container = DependencyContainer()
    container.override_llm(mock_llm)
    return container


@pytest.fixture
def test_factory(test_container):
    """
    AgentFactory instance with mocked dependencies.
    
    Usage:
        def test_example(test_factory):
            agent = test_factory.create("legal")
    """
    return test_container.agent_factory


# =============================================================================
# LOGGER FIXTURES
# =============================================================================


@pytest.fixture
def mock_logger():
    """
    Mock logger for testing agent logging behavior.
    
    Usage:
        def test_example(mock_logger):
            agent = SomeAgent(llm=mock_llm, logger=mock_logger)
            mock_logger.node_enter.assert_called_once()
    """
    logger = MagicMock()
    logger.node_enter = MagicMock()
    logger.node_exit = MagicMock()
    logger.debug = MagicMock()
    logger.error = MagicMock()
    return logger


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
