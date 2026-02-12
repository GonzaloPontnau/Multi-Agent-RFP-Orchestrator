"""
RFP Document Loader - Implementation

Production-grade PDF ingestion engine with hybrid extraction:
- Native text extraction via pdfplumber
- OCR fallback via pytesseract for scanned documents
- Table detection and Markdown conversion
- Header/footer noise reduction
- Semantic chunking with rich metadata

Author: TenderCortex Team
"""

import logging
import os
import re
from collections import Counter
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Support both package import and standalone loading
try:
    from .definition import (
        DocumentChunk,
        EncryptedPDFError,
        InvalidPDFError,
        ProcessingStrategy,
        ProcessingTimeoutError,
        RFPLoaderInput,
        RFPLoaderOutput,
    )
except ImportError:
    # Fallback for standalone testing
    from definition import (
        DocumentChunk,
        EncryptedPDFError,
        InvalidPDFError,
        ProcessingStrategy,
        ProcessingTimeoutError,
        RFPLoaderInput,
        RFPLoaderOutput,
    )

logger = logging.getLogger(__name__)


class RFPLoader:
    """
    Production-grade PDF loader for RFP documents.
    
    Implements a hybrid ingestion engine that automatically detects
    the best extraction strategy and preserves document structure.
    
    Usage:
        loader = RFPLoader()
        result = loader.load("/path/to/rfp.pdf")
        for chunk in result.chunks:
            print(f"Page {chunk.page_number}: {chunk.content[:100]}...")
    
    Raises:
        EncryptedPDFError: If PDF is password-protected
        InvalidPDFError: If file is not a valid PDF
        ProcessingTimeoutError: If document exceeds page limit
        FileNotFoundError: If file does not exist
    """
    
    # Chunk size configuration
    DEFAULT_CHUNK_SIZE = 1000  # characters
    DEFAULT_CHUNK_OVERLAP = 200  # characters
    
    # OCR configuration
    OCR_LANG = "spa+eng"  # Spanish + English
    OCR_CONFIG = "--oem 3 --psm 6"  # LSTM engine, block of text
    
    # Noise detection thresholds
    HEADER_FOOTER_LINES = 3  # Lines to check for repetitive content
    REPETITION_THRESHOLD = 0.7  # 70% of pages must have same text
    
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        """
        Initialize the RFP Loader.
        
        Args:
            chunk_size: Maximum characters per chunk.
            chunk_overlap: Overlap between consecutive chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Validate dependencies
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError(
                "pdfplumber is required for RFPLoader. "
                "Install with: pip install pdfplumber"
            )
    
    def load(
        self,
        file_path: str,
        strategy: ProcessingStrategy = ProcessingStrategy.HI_RES,
        extract_tables: bool = True,
        max_pages: int = 500,
    ) -> RFPLoaderOutput:
        """
        Load and process a PDF document.
        
        This is the main entry point. It validates the input, detects
        the best extraction strategy, and returns structured chunks.
        
        Args:
            file_path: Absolute path to the PDF file.
            strategy: Processing strategy (FAST, OCR_ONLY, HI_RES).
            extract_tables: Whether to detect and convert tables.
            max_pages: Maximum pages to process before timeout.
        
        Returns:
            RFPLoaderOutput with chunks and processing metadata.
        
        Raises:
            FileNotFoundError: If file does not exist.
            EncryptedPDFError: If PDF is password-protected.
            InvalidPDFError: If file is not a valid PDF.
            ProcessingTimeoutError: If document exceeds max_pages.
        """
        # Validate input
        input_data = RFPLoaderInput(
            file_path=file_path,
            strategy=strategy,
            extract_tables=extract_tables,
            max_pages=max_pages,
        )
        
        path = Path(input_data.file_path)
        
        # Check file exists
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        # Validate MIME type (basic check)
        if not self._is_valid_pdf(path):
            raise InvalidPDFError(file_path, "No es un archivo PDF válido")
        
        logger.info(f"Procesando PDF: {path.name} (strategy={strategy.value})")
        
        try:
            return self._process_pdf(
                path=path,
                strategy=strategy,
                extract_tables=extract_tables,
                max_pages=max_pages,
            )
        except Exception as e:
            # Catch pdfplumber specific errors
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypt" in error_msg:
                raise EncryptedPDFError(file_path)
            if "pdf" in error_msg and ("invalid" in error_msg or "corrupt" in error_msg):
                raise InvalidPDFError(file_path, str(e))
            raise
    
    def _is_valid_pdf(self, path: Path) -> bool:
        """Check if file is a valid PDF by reading magic bytes."""
        try:
            with open(path, "rb") as f:
                header = f.read(5)
                return header == b"%PDF-"
        except Exception:
            return False
    
    def _process_pdf(
        self,
        path: Path,
        strategy: ProcessingStrategy,
        extract_tables: bool,
        max_pages: int,
    ) -> RFPLoaderOutput:
        """Core PDF processing logic."""
        chunks: list[DocumentChunk] = []
        warnings: list[str] = []
        tables_extracted = 0
        ocr_used = False
        
        with pdfplumber.open(path) as pdf:
            total_pages = len(pdf.pages)
            
            # Check page limit
            if total_pages > max_pages:
                raise ProcessingTimeoutError(str(path), total_pages, max_pages)
            
            # Collect all page texts for noise detection
            page_texts: list[tuple[int, str, list[str]]] = []
            
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text based on strategy
                if strategy == ProcessingStrategy.OCR_ONLY:
                    text, page_warnings = self._extract_with_ocr(page)
                    ocr_used = True
                    warnings.extend(page_warnings)
                elif strategy == ProcessingStrategy.FAST:
                    text = page.extract_text() or ""
                else:  # HI_RES
                    # Try native first, fallback to OCR if empty
                    text = page.extract_text() or ""
                    if not text.strip() and TESSERACT_AVAILABLE:
                        text, page_warnings = self._extract_with_ocr(page)
                        ocr_used = True
                        warnings.extend(page_warnings)
                
                # Extract tables if requested
                if extract_tables and strategy != ProcessingStrategy.FAST:
                    tables = page.extract_tables()
                    for table in tables:
                        if table and len(table) > 1:  # At least header + 1 row
                            table_md = self._table_to_markdown(table)
                            chunks.append(DocumentChunk(
                                content=table_md,
                                page_number=page_num,
                                chunk_type="table",
                                source_file=path.name,
                                metadata={"table_rows": len(table)},
                            ))
                            tables_extracted += 1
                
                # Store for noise detection
                lines = text.split("\n") if text else []
                page_texts.append((page_num, text, lines))
            
            # Detect and remove headers/footers
            if strategy == ProcessingStrategy.HI_RES:
                noise_patterns = self._detect_noise_patterns(page_texts)
                page_texts = self._remove_noise(page_texts, noise_patterns)
                if noise_patterns:
                    logger.debug(f"Removed {len(noise_patterns)} noise patterns")
            
            # Chunk the cleaned text
            for page_num, text, _ in page_texts:
                if not text.strip():
                    continue
                
                # Semantic chunking
                text_chunks = self._semantic_chunk(text)
                
                for i, chunk_content in enumerate(text_chunks):
                    if chunk_content.strip():
                        chunks.append(DocumentChunk(
                            content=chunk_content.strip(),
                            page_number=page_num,
                            chunk_type="text",
                            source_file=path.name,
                            metadata={"chunk_index": i},
                        ))
        
        logger.info(
            f"Procesado: {total_pages} páginas, {len(chunks)} chunks, "
            f"{tables_extracted} tablas, OCR={'sí' if ocr_used else 'no'}"
        )
        
        return RFPLoaderOutput(
            chunks=chunks,
            total_pages=total_pages,
            processing_strategy=strategy,
            tables_extracted=tables_extracted,
            ocr_used=ocr_used,
            warnings=warnings,
        )
    
    def _extract_with_ocr(self, page) -> tuple[str, list[str]]:
        """Extract text from page using OCR."""
        warnings = []
        
        if not TESSERACT_AVAILABLE:
            warnings.append(
                f"Página {page.page_number}: OCR no disponible (instalar pytesseract)"
            )
            return "", warnings
        
        try:
            # Convert page to image
            img = page.to_image(resolution=300)
            pil_image = img.original
            
            # Run OCR
            text = pytesseract.image_to_string(
                pil_image,
                lang=self.OCR_LANG,
                config=self.OCR_CONFIG,
            )
            
            return text, warnings
        except Exception as e:
            warnings.append(f"Página {page.page_number}: Error OCR - {e}")
            return "", warnings
    
    def _table_to_markdown(self, table: list[list]) -> str:
        """Convert a table (list of rows) to Markdown pipe format."""
        if not table:
            return ""
        
        # Clean cells
        cleaned = []
        for row in table:
            cleaned_row = []
            for cell in row:
                cell_text = str(cell) if cell is not None else ""
                # Remove newlines and excessive whitespace
                cell_text = re.sub(r"\s+", " ", cell_text).strip()
                # Escape pipes
                cell_text = cell_text.replace("|", "\\|")
                cleaned_row.append(cell_text)
            cleaned.append(cleaned_row)
        
        if not cleaned:
            return ""
        
        # Build Markdown table
        lines = []
        
        # Header row
        header = cleaned[0]
        lines.append("| " + " | ".join(header) + " |")
        
        # Separator
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        
        # Data rows
        for row in cleaned[1:]:
            # Pad row if necessary
            while len(row) < len(header):
                row.append("")
            lines.append("| " + " | ".join(row[:len(header)]) + " |")
        
        return "\n".join(lines)
    
    def _detect_noise_patterns(
        self,
        page_texts: list[tuple[int, str, list[str]]],
    ) -> set[str]:
        """
        Detect repetitive headers/footers across pages.
        
        Looks at the first and last N lines of each page and identifies
        patterns that repeat in >70% of pages (likely headers/footers).
        """
        if len(page_texts) < 3:
            return set()
        
        # Collect candidate noise lines
        header_candidates: list[str] = []
        footer_candidates: list[str] = []
        
        for _, _, lines in page_texts:
            if not lines:
                continue
            
            # Get first/last lines
            headers = lines[:self.HEADER_FOOTER_LINES]
            footers = lines[-self.HEADER_FOOTER_LINES:]
            
            for line in headers:
                # Normalize (remove page numbers, dates)
                normalized = self._normalize_noise_line(line)
                if normalized and len(normalized) > 5:
                    header_candidates.append(normalized)
            
            for line in footers:
                normalized = self._normalize_noise_line(line)
                if normalized and len(normalized) > 5:
                    footer_candidates.append(normalized)
        
        # Find repetitive patterns
        noise_patterns = set()
        threshold = len(page_texts) * self.REPETITION_THRESHOLD
        
        for candidates in [header_candidates, footer_candidates]:
            counts = Counter(candidates)
            for pattern, count in counts.items():
                if count >= threshold:
                    noise_patterns.add(pattern)
        
        return noise_patterns
    
    def _normalize_noise_line(self, line: str) -> str:
        """
        Normalize a line for noise detection.
        
        Removes page numbers, dates, and excessive whitespace.
        """
        if not line:
            return ""
        
        # Remove common page number patterns
        line = re.sub(r"\b(página|page|pág\.?)\s*\d+\b", "", line, flags=re.IGNORECASE)
        line = re.sub(r"\b\d+\s*(de|of|/)\s*\d+\b", "", line)
        line = re.sub(r"^\s*\d+\s*$", "", line)  # Standalone numbers
        
        # Remove dates
        line = re.sub(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", "", line)
        
        # Normalize whitespace
        line = re.sub(r"\s+", " ", line).strip()
        
        return line
    
    def _remove_noise(
        self,
        page_texts: list[tuple[int, str, list[str]]],
        noise_patterns: set[str],
    ) -> list[tuple[int, str, list[str]]]:
        """Remove detected noise patterns from page texts."""
        if not noise_patterns:
            return page_texts
        
        cleaned = []
        for page_num, text, lines in page_texts:
            clean_lines = []
            for line in lines:
                normalized = self._normalize_noise_line(line)
                if normalized not in noise_patterns:
                    clean_lines.append(line)
            
            clean_text = "\n".join(clean_lines)
            cleaned.append((page_num, clean_text, clean_lines))
        
        return cleaned
    
    def _semantic_chunk(self, text: str) -> list[str]:
        """
        Split text into semantic chunks.
        
        Respects paragraph boundaries and attempts to keep
        related content together.
        """
        if not text:
            return []
        
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r"\n\n+", text)
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(para) + 2 > self.chunk_size:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If paragraph itself is too long, split it
                if len(para) > self.chunk_size:
                    # Split by sentences
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    sub_chunk = ""
                    
                    for sentence in sentences:
                        if len(sub_chunk) + len(sentence) + 1 > self.chunk_size:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = sentence
                        else:
                            sub_chunk = (sub_chunk + " " + sentence).strip()
                    
                    if sub_chunk:
                        current_chunk = sub_chunk
                else:
                    current_chunk = para
            else:
                current_chunk = (current_chunk + "\n\n" + para).strip()
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks


# Convenience function for simple usage
def load_rfp_document(
    file_path: str,
    strategy: str = "hi_res",
    extract_tables: bool = True,
) -> RFPLoaderOutput:
    """
    Load an RFP document with default settings.
    
    This is a convenience function for simple use cases.
    For more control, instantiate RFPLoader directly.
    
    Args:
        file_path: Path to the PDF file.
        strategy: "fast", "ocr_only", or "hi_res".
        extract_tables: Whether to extract tables.
    
    Returns:
        RFPLoaderOutput with processed chunks.
    """
    loader = RFPLoader()
    return loader.load(
        file_path=file_path,
        strategy=ProcessingStrategy(strategy),
        extract_tables=extract_tables,
    )
