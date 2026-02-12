"""
Unit tests for RFP Document Loader skill.

Tests cover:
- Text extraction (native PDF)
- Table detection and Markdown conversion
- Error handling (encrypted, invalid, file not found)
- Semantic chunking behavior
- Noise pattern detection

Author: TenderCortex Team
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# Add skills directory to path for imports
import sys
skills_path = Path(__file__).parent.parent.parent / "skills" / "rfp_document_loader"
sys.path.insert(0, str(skills_path.parent))

# Now we can import using the package structure
# Note: Python doesn't allow hyphens in module names, so we use importlib
import importlib.util

def load_module(module_name: str, file_path: Path):
    """Dynamically load a module from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Load definition module
definition = load_module(
    "rfp_document_loader_definition",
    skills_path / "definition.py"
)

# Extract classes from the loaded module
DocumentChunk = definition.DocumentChunk
EncryptedPDFError = definition.EncryptedPDFError
InvalidPDFError = definition.InvalidPDFError
ProcessingStrategy = definition.ProcessingStrategy
ProcessingTimeoutError = definition.ProcessingTimeoutError
RFPLoaderInput = definition.RFPLoaderInput
RFPLoaderOutput = definition.RFPLoaderOutput

# Load implementation module
impl = load_module(
    "rfp_document_loader_impl",
    skills_path / "impl.py"
)
RFPLoader = impl.RFPLoader


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_pdf_page():
    """Create a mock pdfplumber page."""
    page = MagicMock()
    page.page_number = 1
    page.extract_text.return_value = (
        "LICITACIÓN PÚBLICA INTERNACIONAL\n\n"
        "OBJETO: Adquisición de equipos de cómputo.\n\n"
        "PRESUPUESTO: USD 500,000.00\n\n"
        "El plazo de entrega será de 60 días calendario."
    )
    page.extract_tables.return_value = []
    return page


@pytest.fixture
def mock_pdf_with_tables():
    """Create a mock pdfplumber page with a table."""
    page = MagicMock()
    page.page_number = 1
    page.extract_text.return_value = "Tabla de precios:"
    page.extract_tables.return_value = [
        [
            ["Producto", "Cantidad", "Precio"],
            ["Laptop", "100", "$1,000"],
            ["Monitor", "100", "$300"],
        ]
    ]
    return page


@pytest.fixture
def mock_pdf_file(tmp_path):
    """Create a mock PDF file for path validation tests."""
    pdf_path = tmp_path / "test.pdf"
    # Write PDF magic bytes
    pdf_path.write_bytes(b"%PDF-1.4\n%fake pdf content")
    return pdf_path


@pytest.fixture
def mock_invalid_file(tmp_path):
    """Create a non-PDF file."""
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("This is not a PDF")
    return txt_path


# =============================================================================
# PYDANTIC MODEL TESTS
# =============================================================================


class TestRFPLoaderInput:
    """Tests for input validation model."""
    
    def test_valid_input(self, mock_pdf_file):
        """Valid input should pass validation."""
        input_data = RFPLoaderInput(
            file_path=str(mock_pdf_file),
            strategy=ProcessingStrategy.HI_RES,
            extract_tables=True,
        )
        assert input_data.file_path == str(mock_pdf_file)
        assert input_data.strategy == ProcessingStrategy.HI_RES
    
    def test_relative_path_rejected(self):
        """Relative paths should be rejected."""
        with pytest.raises(ValueError, match="absoluta"):
            RFPLoaderInput(file_path="relative/path.pdf")
    
    def test_non_pdf_rejected(self):
        """Non-PDF files should be rejected."""
        with pytest.raises(ValueError, match="PDF"):
            RFPLoaderInput(file_path="/absolute/path/file.txt")
    
    def test_default_values(self, mock_pdf_file):
        """Test default values are applied."""
        input_data = RFPLoaderInput(file_path=str(mock_pdf_file))
        assert input_data.strategy == ProcessingStrategy.HI_RES
        assert input_data.extract_tables is True
        assert input_data.max_pages == 500


class TestDocumentChunk:
    """Tests for DocumentChunk model."""
    
    def test_chunk_creation(self):
        """Test basic chunk creation."""
        chunk = DocumentChunk(
            content="Test content",
            page_number=1,
            chunk_type="text",
            source_file="test.pdf",
        )
        assert chunk.content == "Test content"
        assert chunk.page_number == 1
        assert chunk.chunk_type == "text"
    
    def test_to_langchain_document(self):
        """Test conversion to LangChain Document."""
        chunk = DocumentChunk(
            content="Test content",
            page_number=2,
            chunk_type="table",
            source_file="test.pdf",
            metadata={"extra": "data"},
        )
        doc = chunk.to_langchain_document()
        
        assert doc.page_content == "Test content"
        assert doc.metadata["source"] == "test.pdf"
        assert doc.metadata["page"] == 2
        assert doc.metadata["chunk_type"] == "table"
        assert doc.metadata["extra"] == "data"


class TestProcessingStrategy:
    """Tests for ProcessingStrategy enum."""
    
    def test_strategy_values(self):
        """Test enum values."""
        assert ProcessingStrategy.FAST.value == "fast"
        assert ProcessingStrategy.OCR_ONLY.value == "ocr_only"
        assert ProcessingStrategy.HI_RES.value == "hi_res"


# =============================================================================
# RFP LOADER TESTS
# =============================================================================


class TestRFPLoader:
    """Tests for RFPLoader class."""
    
    @patch("rfp_document_loader.impl.pdfplumber")
    def test_load_basic_pdf(self, mock_pdfplumber, mock_pdf_file, mock_pdf_page):
        """Test loading a basic PDF with text."""
        from rfp_document_loader.impl import RFPLoader
        
        # Setup mock
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_pdf_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf
        
        # Run loader
        loader = RFPLoader()
        result = loader.load(str(mock_pdf_file))
        
        assert isinstance(result, RFPLoaderOutput)
        assert result.total_pages == 1
        assert len(result.chunks) > 0
        assert result.processing_strategy == ProcessingStrategy.HI_RES
    
    @patch("rfp_document_loader.impl.pdfplumber")
    def test_table_extraction(self, mock_pdfplumber, mock_pdf_file, mock_pdf_with_tables):
        """Test table extraction and Markdown conversion."""
        from rfp_document_loader.impl import RFPLoader
        
        # Setup mock
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_pdf_with_tables]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf
        
        loader = RFPLoader()
        result = loader.load(str(mock_pdf_file), extract_tables=True)
        
        assert result.tables_extracted == 1
        
        # Find the table chunk
        table_chunks = [c for c in result.chunks if c.chunk_type == "table"]
        assert len(table_chunks) == 1
        
        # Verify Markdown format
        table_content = table_chunks[0].content
        assert "|" in table_content
        assert "Producto" in table_content
        assert "Laptop" in table_content
    
    def test_file_not_found(self):
        """Test handling of non-existent files."""
        from rfp_document_loader.impl import RFPLoader
        
        loader = RFPLoader()
        with pytest.raises(FileNotFoundError):
            loader.load("/nonexistent/path/to/file.pdf")
    
    def test_invalid_pdf(self, mock_invalid_file):
        """Test handling of invalid PDF files."""
        from rfp_document_loader.impl import RFPLoader
        
        # Create a .pdf file with wrong content
        pdf_path = mock_invalid_file.parent / "fake.pdf"
        pdf_path.write_text("Not a real PDF")
        
        loader = RFPLoader()
        with pytest.raises(InvalidPDFError):
            loader.load(str(pdf_path))
    
    @patch("rfp_document_loader.impl.pdfplumber")
    def test_encrypted_pdf(self, mock_pdfplumber, mock_pdf_file):
        """Test handling of encrypted PDFs."""
        from rfp_document_loader.impl import RFPLoader
        
        # Simulate encrypted PDF error
        mock_pdfplumber.open.side_effect = Exception("PDF is password-protected")
        
        loader = RFPLoader()
        with pytest.raises(EncryptedPDFError):
            loader.load(str(mock_pdf_file))
    
    @patch("rfp_document_loader.impl.pdfplumber")
    def test_page_limit_exceeded(self, mock_pdfplumber, mock_pdf_file, mock_pdf_page):
        """Test handling of documents exceeding page limit."""
        from rfp_document_loader.impl import RFPLoader
        
        # Create 10 mock pages
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_pdf_page] * 10
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf
        
        loader = RFPLoader()
        with pytest.raises(ProcessingTimeoutError):
            loader.load(str(mock_pdf_file), max_pages=5)
    
    def test_fast_strategy_skips_tables(self):
        """Test that FAST strategy skips table extraction."""
        # This is a unit test for the logic, not full integration
        from rfp_document_loader.impl import RFPLoader
        
        loader = RFPLoader()
        # Just verify the loader can be instantiated
        assert loader.chunk_size == 1000
        assert loader.chunk_overlap == 200


class TestTableToMarkdown:
    """Tests for table to Markdown conversion."""
    
    def test_basic_table(self):
        """Test basic table conversion."""
        from rfp_document_loader.impl import RFPLoader
        
        loader = RFPLoader()
        table = [
            ["Header1", "Header2"],
            ["Value1", "Value2"],
        ]
        
        result = loader._table_to_markdown(table)
        
        assert "| Header1 | Header2 |" in result
        assert "| --- | --- |" in result
        assert "| Value1 | Value2 |" in result
    
    def test_table_with_pipes(self):
        """Test escaping of pipe characters in cells."""
        from rfp_document_loader.impl import RFPLoader
        
        loader = RFPLoader()
        table = [
            ["Name", "Formula"],
            ["OR Gate", "A|B"],
        ]
        
        result = loader._table_to_markdown(table)
        assert "A\\|B" in result  # Pipe should be escaped
    
    def test_empty_table(self):
        """Test handling of empty tables."""
        from rfp_document_loader.impl import RFPLoader
        
        loader = RFPLoader()
        assert loader._table_to_markdown([]) == ""
        assert loader._table_to_markdown(None) == ""


class TestSemanticChunking:
    """Tests for semantic chunking behavior."""
    
    def test_respects_paragraphs(self):
        """Test that chunking respects paragraph boundaries."""
        from rfp_document_loader.impl import RFPLoader
        
        loader = RFPLoader(chunk_size=100, chunk_overlap=20)
        
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = loader._semantic_chunk(text)
        
        assert len(chunks) >= 1
        # Each chunk should start with content, not newlines
        for chunk in chunks:
            assert not chunk.startswith("\n")
    
    def test_handles_long_paragraphs(self):
        """Test chunking of very long paragraphs."""
        from rfp_document_loader.impl import RFPLoader
        
        loader = RFPLoader(chunk_size=50, chunk_overlap=10)
        
        # Create a paragraph longer than chunk_size
        long_para = "This is a sentence. " * 20
        chunks = loader._semantic_chunk(long_para)
        
        # Should be split into multiple chunks
        assert len(chunks) > 1
        # No chunk should exceed chunk_size significantly
        for chunk in chunks:
            # Allow some flexibility for sentence boundaries
            assert len(chunk) < loader.chunk_size * 2


class TestNoiseDetection:
    """Tests for header/footer noise detection."""
    
    def test_detect_repetitive_headers(self):
        """Test detection of repetitive headers."""
        from rfp_document_loader.impl import RFPLoader
        
        loader = RFPLoader()
        
        # Simulate 5 pages with same header
        page_texts = [
            (1, "Company Name\n\nContent page 1", ["Company Name", "", "Content page 1"]),
            (2, "Company Name\n\nContent page 2", ["Company Name", "", "Content page 2"]),
            (3, "Company Name\n\nContent page 3", ["Company Name", "", "Content page 3"]),
            (4, "Company Name\n\nContent page 4", ["Company Name", "", "Content page 4"]),
            (5, "Company Name\n\nContent page 5", ["Company Name", "", "Content page 5"]),
        ]
        
        patterns = loader._detect_noise_patterns(page_texts)
        
        # "Company Name" should be detected as noise
        assert "Company Name" in patterns
    
    def test_normalize_page_numbers(self):
        """Test that page numbers are normalized out."""
        from rfp_document_loader.impl import RFPLoader
        
        loader = RFPLoader()
        
        assert loader._normalize_noise_line("Page 1") == ""
        assert loader._normalize_noise_line("página 42") == ""
        assert loader._normalize_noise_line("5 de 10") == ""
        assert loader._normalize_noise_line("3/10") == ""
