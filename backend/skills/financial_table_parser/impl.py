"""
Financial Table Parser - Implementation

Deterministic financial table extraction from PDF documents.
Features:
- pdfplumber-based grid extraction
- Merged cell handling
- Currency string sanitization
- Financial keyword detection
- Structured numerical output

Author: TenderCortex Team
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from .definition import (
        CurrencyType,
        ExtractionResult,
        FinancialParserError,
        FinancialRow,
        FinancialTableOutput,
        InvalidPageRangeError,
        NoTablesFoundError,
        ScannedDocumentError,
        TableExtractionInput,
    )
except ImportError:
    from definition import (
        CurrencyType,
        ExtractionResult,
        FinancialParserError,
        FinancialRow,
        FinancialTableOutput,
        InvalidPageRangeError,
        NoTablesFoundError,
        ScannedDocumentError,
        TableExtractionInput,
    )

logger = logging.getLogger(__name__)


# Financial keywords for table detection
FINANCIAL_KEYWORDS = {
    # Spanish
    "precio", "precios", "monto", "montos", "total", "totales",
    "subtotal", "costo", "costos", "valor", "valores", "importe",
    "importes", "unidad", "unitario", "cantidad", "cant", "iva",
    "impuesto", "descuento", "neto", "bruto",
    # English
    "price", "prices", "amount", "amounts", "cost", "costs",
    "value", "values", "unit", "quantity", "qty", "tax",
    "discount", "net", "gross", "subtotal", "fee", "rate",
    # Currency symbols
    "$", "€", "£", "¥", "usd", "eur", "ars", "brl", "mxn",
}

# Column name mappings for fuzzy matching
COLUMN_MAPPINGS = {
    "description": ["descripcion", "descripción", "concepto", "item", "ítem",
                    "producto", "servicio", "detalle", "rubro", "name", "nombre"],
    "unit_price": ["precio_unitario", "precio_unit", "p_unit", "unit_price",
                   "precio", "price", "tarifa", "rate", "costo_unitario"],
    "quantity": ["cantidad", "cant", "qty", "quantity", "unidades", "units",
                 "volumen", "volume"],
    "total_price": ["total", "importe", "monto", "subtotal", "amount",
                    "precio_total", "total_price", "valor", "value"],
}


class FinancialTableParser:
    """
    Deterministic financial table extractor for PDF documents.
    
    Extracts tables with monetary data, cleans currency strings,
    and returns structured numerical data ready for calculations.
    
    Usage:
        parser = FinancialTableParser()
        result = parser.extract(
            file_path="/docs/quotation.pdf",
            page_range="10-15"
        )
        
        for table in result.tables:
            print(f"Table {table.table_id}: Total = ${table.total_detected:,.2f}")
    
    Raises:
        NoTablesFoundError: If no tables found in specified pages
        InvalidPageRangeError: If page range is invalid
        ScannedDocumentError: If document appears to be scanned image
    """
    
    def __init__(self):
        """Initialize the Financial Table Parser."""
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError(
                "pdfplumber is required for FinancialTableParser. "
                "Install with: pip install pdfplumber"
            )
    
    def extract(
        self,
        file_path: str,
        page_range: str,
        currency_hint: CurrencyType = CurrencyType.USD,
        confidence_threshold: float = 0.5,
        include_raw_data: bool = True,
    ) -> ExtractionResult:
        """
        Extract financial tables from a PDF document.
        
        Args:
            file_path: Absolute path to the PDF file.
            page_range: Pages to analyze ("5-10", "15", "1,3,5-7", "all").
            currency_hint: Default currency if not detected.
            confidence_threshold: Minimum confidence to include table.
            include_raw_data: Whether to include raw data for auditing.
        
        Returns:
            ExtractionResult with all extracted tables.
        
        Raises:
            NoTablesFoundError: If no tables found.
            InvalidPageRangeError: If page range is invalid.
        """
        # Validate input
        input_data = TableExtractionInput(
            file_path=file_path,
            page_range=page_range,
            currency_hint=currency_hint,
            confidence_threshold=confidence_threshold,
            include_raw_data=include_raw_data,
        )
        
        path = Path(input_data.file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        logger.info(f"Extracting financial tables from: {path.name}, pages: {page_range}")
        
        all_tables: List[FinancialTableOutput] = []
        global_warnings: List[str] = []
        pages_processed: List[int] = []
        total_tables_found = 0
        
        with pdfplumber.open(path) as pdf:
            # Parse page range
            page_numbers = self._parse_page_range(page_range, len(pdf.pages))
            
            table_id = 1
            for page_num in page_numbers:
                page = pdf.pages[page_num - 1]  # 0-indexed
                pages_processed.append(page_num)
                
                # Check if page has text (not scanned)
                text = page.extract_text()
                if not text or len(text.strip()) < 10:
                    global_warnings.append(
                        f"Página {page_num}: Poco o ningún texto detectado (posible escaneo)"
                    )
                    continue
                
                # Extract tables from page
                page_tables = page.extract_tables()
                
                for raw_table in page_tables:
                    if not raw_table or len(raw_table) < 2:
                        continue
                    
                    total_tables_found += 1
                    
                    # Process and validate table
                    processed = self._process_table(
                        raw_table=raw_table,
                        table_id=table_id,
                        page_number=page_num,
                        currency_hint=currency_hint.value,
                        include_raw_data=include_raw_data,
                    )
                    
                    # Filter by confidence
                    if processed.confidence >= confidence_threshold:
                        all_tables.append(processed)
                        table_id += 1
                    else:
                        global_warnings.append(
                            f"Tabla en pág. {page_num} descartada "
                            f"(confianza {processed.confidence:.2f} < {confidence_threshold})"
                        )
        
        # Calculate grand total
        grand_total = sum(t.total_detected for t in all_tables)
        
        if not all_tables and total_tables_found == 0:
            raise NoTablesFoundError(pages_processed)
        
        logger.info(
            f"Extracted {len(all_tables)} financial tables "
            f"(of {total_tables_found} total), grand total: {grand_total:,.2f}"
        )
        
        return ExtractionResult(
            tables=all_tables,
            file_path=str(path),
            pages_processed=pages_processed,
            total_tables_found=total_tables_found,
            grand_total=grand_total,
            warnings=global_warnings,
        )
    
    def _parse_page_range(self, page_range: str, max_pages: int) -> List[int]:
        """Parse page range string into list of page numbers."""
        page_range = page_range.strip().lower()
        
        if page_range == "all":
            return list(range(1, max_pages + 1))
        
        pages = set()
        parts = page_range.replace(" ", "").split(",")
        
        for part in parts:
            if "-" in part:
                start, end = part.split("-", 1)
                try:
                    start_num = int(start)
                    end_num = int(end)
                    for p in range(start_num, end_num + 1):
                        if 1 <= p <= max_pages:
                            pages.add(p)
                except ValueError:
                    raise InvalidPageRangeError(page_range, max_pages)
            else:
                try:
                    p = int(part)
                    if 1 <= p <= max_pages:
                        pages.add(p)
                except ValueError:
                    raise InvalidPageRangeError(page_range, max_pages)
        
        if not pages:
            raise InvalidPageRangeError(page_range, max_pages)
        
        return sorted(pages)
    
    def _process_table(
        self,
        raw_table: List[List],
        table_id: int,
        page_number: int,
        currency_hint: str,
        include_raw_data: bool,
    ) -> FinancialTableOutput:
        """Process a raw table into structured financial data."""
        warnings = []
        
        # Clean and extract headers
        headers_original = [str(h or "").strip() for h in raw_table[0]]
        headers = [self._normalize_header(h) for h in headers_original]
        
        # Calculate financial confidence
        confidence, currency_detected = self._calculate_financial_confidence(
            headers_original, raw_table
        )
        
        # Map columns to standard fields
        column_mapping = self._map_columns(headers)
        
        # Handle merged cells - propagate values down
        processed_rows = self._handle_merged_cells(raw_table[1:])
        
        # Parse each row
        financial_rows = []
        totals_column_values = []
        
        for row_idx, row in enumerate(processed_rows):
            row_data = self._parse_row(
                row=row,
                headers=headers,
                column_mapping=column_mapping,
                row_index=row_idx,
                currency_hint=currency_hint,
                include_raw_data=include_raw_data,
            )
            
            if row_data:
                financial_rows.append(row_data)
                if row_data.total_price is not None:
                    totals_column_values.append(row_data.total_price)
        
        # Calculate detected total
        total_detected = sum(totals_column_values) if totals_column_values else 0.0
        
        return FinancialTableOutput(
            table_id=table_id,
            page_number=page_number,
            headers=headers,
            headers_original=headers_original,
            rows=financial_rows,
            total_detected=total_detected,
            confidence=confidence,
            currency_detected=currency_detected or currency_hint,
            warnings=warnings,
        )
    
    def _normalize_header(self, header: str) -> str:
        """Normalize header to snake_case."""
        if not header:
            return "column"
        
        # Remove special characters, convert to lowercase
        normalized = re.sub(r'[^\w\s]', '', header.lower())
        # Replace spaces with underscores
        normalized = re.sub(r'\s+', '_', normalized.strip())
        # Remove multiple underscores
        normalized = re.sub(r'_+', '_', normalized)
        
        return normalized or "column"
    
    def _calculate_financial_confidence(
        self,
        headers: List[str],
        table: List[List],
    ) -> Tuple[float, Optional[str]]:
        """
        Calculate confidence that this table contains financial data.
        
        Returns (confidence_score, detected_currency)
        """
        score = 0.0
        currency_detected = None
        
        # Check headers for financial keywords
        header_text = " ".join(headers).lower()
        for keyword in FINANCIAL_KEYWORDS:
            if keyword in header_text:
                score += 0.15
                if keyword in ("$", "usd"):
                    currency_detected = "USD"
                elif keyword in ("€", "eur"):
                    currency_detected = "EUR"
                elif keyword == "ars":
                    currency_detected = "ARS"
        
        # Check content for currency symbols and numbers
        content_sample = []
        for row in table[1:5]:  # Sample first 4 data rows
            for cell in row:
                if cell:
                    content_sample.append(str(cell).lower())
        
        content_text = " ".join(content_sample)
        
        # Check for currency symbols
        if "$" in content_text:
            score += 0.2
            currency_detected = currency_detected or "USD"
        if "€" in content_text:
            score += 0.2
            currency_detected = currency_detected or "EUR"
        
        # Check for numeric patterns (prices)
        price_pattern = r'[\d.,]+(?:\s*(?:usd|ars|eur|\$|€))?'
        if re.search(price_pattern, content_text):
            score += 0.2
        
        # Check for typical financial column count (3-10 columns)
        if 3 <= len(headers) <= 10:
            score += 0.1
        
        return min(score, 1.0), currency_detected
    
    def _map_columns(self, headers: List[str]) -> Dict[str, int]:
        """Map normalized headers to standard column names."""
        mapping = {}
        
        for std_name, variations in COLUMN_MAPPINGS.items():
            for idx, header in enumerate(headers):
                if header in variations or any(v in header for v in variations):
                    if std_name not in mapping:
                        mapping[std_name] = idx
                    break
        
        # Fallback: guess by position if not mapped
        if "description" not in mapping and len(headers) > 0:
            mapping["description"] = 0  # First column usually description
        
        if "total_price" not in mapping:
            # Last numeric-looking column is often total
            for idx in range(len(headers) - 1, -1, -1):
                if any(kw in headers[idx] for kw in ["total", "monto", "importe", "amount"]):
                    mapping["total_price"] = idx
                    break
        
        return mapping
    
    def _handle_merged_cells(self, rows: List[List]) -> List[List]:
        """
        Handle vertically merged cells by propagating values down.
        
        When a cell is empty but previous row had value, propagate it.
        """
        if not rows:
            return rows
        
        processed = []
        previous_row = None
        
        for row in rows:
            new_row = []
            for idx, cell in enumerate(row):
                if cell is None or (isinstance(cell, str) and not cell.strip()):
                    # Empty cell - check if we should propagate from previous
                    if previous_row and idx < len(previous_row):
                        # Only propagate first column (usually category/description)
                        if idx == 0:
                            new_row.append(previous_row[idx])
                        else:
                            new_row.append(cell)
                    else:
                        new_row.append(cell)
                else:
                    new_row.append(cell)
            
            processed.append(new_row)
            previous_row = new_row
        
        return processed
    
    def _parse_row(
        self,
        row: List,
        headers: List[str],
        column_mapping: Dict[str, int],
        row_index: int,
        currency_hint: str,
        include_raw_data: bool,
    ) -> Optional[FinancialRow]:
        """Parse a single row into a FinancialRow."""
        # Skip empty rows
        if not row or all(not cell for cell in row):
            return None
        
        # Build raw data dict
        raw_data = {}
        if include_raw_data:
            for idx, cell in enumerate(row):
                header = headers[idx] if idx < len(headers) else f"col_{idx}"
                raw_data[header] = cell
        
        # Extract mapped values
        description = ""
        if "description" in column_mapping:
            idx = column_mapping["description"]
            if idx < len(row):
                description = str(row[idx] or "").strip()
        
        unit_price = None
        if "unit_price" in column_mapping:
            idx = column_mapping["unit_price"]
            if idx < len(row):
                unit_price = self._clean_currency_string(row[idx])
        
        quantity = None
        if "quantity" in column_mapping:
            idx = column_mapping["quantity"]
            if idx < len(row):
                quantity = self._clean_currency_string(row[idx])
        
        total_price = None
        if "total_price" in column_mapping:
            idx = column_mapping["total_price"]
            if idx < len(row):
                total_price = self._clean_currency_string(row[idx])
        
        # Skip rows that have no description and no numeric values
        if not description and unit_price is None and total_price is None:
            return None
        
        return FinancialRow(
            row_index=row_index,
            description=description,
            unit_price=unit_price,
            quantity=quantity,
            total_price=total_price,
            category=None,  # Could be enhanced with category detection
            raw_data=raw_data,
        )
    
    def _clean_currency_string(self, value: Any) -> Optional[float]:
        """
        Clean and convert a currency string to float.
        
        Handles multiple formats:
        - "$ 1.500,00" -> 1500.0
        - "1,500.00 USD" -> 1500.0
        - "(500)" -> -500.0
        - "€ 2.345,67" -> 2345.67
        - "1'234'567.89" -> 1234567.89
        - "-$1,234.56" -> -1234.56
        - "N/A", "-", "" -> None
        """
        if value is None:
            return None
        
        # Convert to string
        text = str(value).strip()
        
        # Handle empty or non-numeric indicators
        if not text or text.lower() in ("n/a", "-", "n.a.", "na", "s/d", "---"):
            return None
        
        # Track if negative
        is_negative = False
        
        # Check for parentheses notation (500) = -500
        if text.startswith("(") and text.endswith(")"):
            is_negative = True
            text = text[1:-1]
        
        # Check for minus sign anywhere at start
        if text.startswith("-") or text.startswith("−"):  # Handle both regular and unicode minus
            is_negative = True
            text = text[1:]
        
        # Remove currency symbols and text explicitly (preserve digits)
        # Remove common currency symbols
        text = re.sub(r'[$€£¥₹₽]', '', text)
        # Remove currency codes
        text = re.sub(r'\b(USD|EUR|ARS|BRL|MXN|CLP|COP|PEN)\b', '', text, flags=re.IGNORECASE)
        # Remove any remaining letters
        text = re.sub(r'[a-zA-Z]', '', text)
        # Keep only digits, dots, commas, apostrophes
        text = re.sub(r"[^\d.,']", '', text)
        
        if not text:
            return None
        
        # Handle different decimal/thousand separator conventions
        # Detect format based on patterns
        
        # Count separators
        dots = text.count(".")
        commas = text.count(",")
        apostrophes = text.count("'")
        
        # Remove apostrophes (Swiss format thousand separator)
        text = text.replace("'", "")
        
        try:
            if dots == 0 and commas == 0:
                # Plain number: "1500"
                result = float(text)
            
            elif dots == 1 and commas == 0:
                # Could be decimal: "1500.50" or thousand: "1.500"
                parts = text.split(".")
                if len(parts[1]) == 3 and len(parts[0]) <= 3:
                    # Likely thousand separator: "1.500" -> 1500
                    result = float(text.replace(".", ""))
                else:
                    # Likely decimal: "1500.50" -> 1500.5
                    result = float(text)
            
            elif commas == 1 and dots == 0:
                # Could be decimal: "1500,50" or thousand: "1,500"
                parts = text.split(",")
                if len(parts[1]) == 3 and len(parts[0]) <= 3:
                    # Likely thousand separator: "1,500" -> 1500
                    result = float(text.replace(",", ""))
                else:
                    # Likely decimal (European): "1500,50" -> 1500.5
                    result = float(text.replace(",", "."))
            
            elif dots >= 1 and commas == 1:
                # Format: "1.234,56" (European) or "1,234.56" (US)
                dot_pos = text.rfind(".")
                comma_pos = text.rfind(",")
                
                if comma_pos > dot_pos:
                    # European: "1.234,56" -> comma is decimal
                    text = text.replace(".", "").replace(",", ".")
                else:
                    # US: "1,234.56" -> dot is decimal
                    text = text.replace(",", "")
                
                result = float(text)
            
            elif commas >= 1 and dots == 1:
                # Format: "1,234,567.89" (US with multiple thousand sep)
                text = text.replace(",", "")
                result = float(text)
            
            elif commas > 1 and dots == 0:
                # Multiple commas as thousand sep: "1,234,567"
                text = text.replace(",", "")
                result = float(text)
            
            elif dots > 1 and commas == 0:
                # Multiple dots as thousand sep: "1.234.567"
                text = text.replace(".", "")
                result = float(text)
            
            else:
                # Fallback: try direct conversion
                result = float(text.replace(",", "").replace(".", ""))
        
        except ValueError:
            return None
        
        return -result if is_negative else result


# Convenience function
def extract_financial_tables(
    file_path: str,
    page_range: str,
    currency_hint: str = "USD",
    confidence_threshold: float = 0.5,
) -> ExtractionResult:
    """
    Extract financial tables with default settings.
    
    Convenience function for simple use cases.
    """
    parser = FinancialTableParser()
    return parser.extract(
        file_path=file_path,
        page_range=page_range,
        currency_hint=CurrencyType(currency_hint),
        confidence_threshold=confidence_threshold,
    )
