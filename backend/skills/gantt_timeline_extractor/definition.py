"""
Gantt Timeline Extractor - Data Definitions

Pydantic models for timeline extraction and normalization.
Supports absolute dates, relative offsets, and dependencies.

Author: TenderCortex Team
"""

from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """
    Taxonomía de eventos temporales en pliegos.
    
    Clasificación basada en criticidad y tipo de hito.
    """
    SUBMISSION_DEADLINE = "submission_deadline"  # ⚠️ Crítico
    QA_DEADLINE = "qa_deadline"
    PROJECT_START = "project_start"
    MILESTONE = "milestone"
    CONTRACT_END = "contract_end"
    MEETING = "meeting"
    PAYMENT = "payment"
    OTHER = "other"


class TimelineEvent(BaseModel):
    """
    Representa un evento temporal extraído del pliego.
    
    Puede ser una fecha absoluta, relativa, o TBD.
    """
    
    date_iso: Optional[str] = Field(
        default=None,
        description="Fecha normalizada YYYY-MM-DD. Null si es TBD o "
                    "depende de otro evento no resuelto."
    )
    
    original_text: str = Field(
        ...,
        description="El texto original detectado tal cual aparece "
                    "en el documento."
    )
    
    description: str = Field(
        ...,
        description="Descripción clara de qué sucede en esta fecha."
    )
    
    event_type: EventType = Field(
        default=EventType.OTHER,
        description="Clasificación del tipo de evento."
    )
    
    is_relative: bool = Field(
        default=False,
        description="True si la fecha fue calculada desde una referencia."
    )
    
    source_page: int = Field(
        ...,
        ge=1,
        description="Número de página donde se encontró el evento."
    )
    
    source_file: Optional[str] = Field(
        default=None,
        description="Nombre del archivo fuente."
    )
    
    dependency: Optional[str] = Field(
        default=None,
        description="Evento del cual depende esta fecha "
                    "(ej. 'adjudicación', 'firma')."
    )
    
    offset_days: Optional[int] = Field(
        default=None,
        description="Días de offset desde la dependencia. "
                    "Positivo = después, Negativo = antes."
    )
    
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confianza en la extracción (0-1)."
    )
    
    is_critical: bool = Field(
        default=False,
        description="True si es un deadline crítico/fatal."
    )
    
    def to_summary(self) -> str:
        """Genera resumen de una línea."""
        date_str = self.date_iso or "TBD"
        critical = "⚠️" if self.is_critical else ""
        return f"{critical} {date_str}: {self.description} [{self.event_type.value}]"


class TimelineOutput(BaseModel):
    """
    Resultado completo de la extracción de cronograma.
    """
    
    events: List[TimelineEvent] = Field(
        default_factory=list,
        description="Lista de eventos ordenados cronológicamente."
    )
    
    anchor_date_used: str = Field(
        ...,
        description="Fecha base utilizada para cálculos relativos (YYYY-MM-DD)."
    )
    
    project_duration_months: Optional[float] = Field(
        default=None,
        description="Duración total del proyecto en meses, si se detecta."
    )
    
    project_duration_days: Optional[int] = Field(
        default=None,
        description="Duración total del proyecto en días, si se detecta."
    )
    
    critical_deadlines: List[TimelineEvent] = Field(
        default_factory=list,
        description="Subconjunto de eventos que son deadlines críticos."
    )
    
    unresolved_events: List[TimelineEvent] = Field(
        default_factory=list,
        description="Eventos con fecha TBD (no resueltos)."
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="Advertencias sobre fechas ambiguas o inferidas."
    )
    
    total_events: int = Field(
        default=0,
        ge=0,
        description="Total de eventos detectados."
    )
    
    def get_next_deadline(self, from_date: str = None) -> Optional[TimelineEvent]:
        """Retorna el próximo deadline desde una fecha dada."""
        from datetime import datetime
        
        ref_date = datetime.strptime(from_date, "%Y-%m-%d").date() if from_date else date.today()
        
        for event in self.critical_deadlines:
            if event.date_iso:
                event_date = datetime.strptime(event.date_iso, "%Y-%m-%d").date()
                if event_date >= ref_date:
                    return event
        return None
    
    def to_markdown_timeline(self) -> str:
        """Genera timeline en formato Markdown."""
        lines = [
            "## Cronograma del Proyecto",
            "",
            f"**Fecha base**: {self.anchor_date_used}",
            f"**Duración estimada**: {self.project_duration_months or 'N/D'} meses",
            "",
            "| Fecha | Evento | Tipo | Crítico |",
            "|-------|--------|------|---------|",
        ]
        
        for event in self.events:
            date_str = event.date_iso or "TBD"
            critical = "⚠️" if event.is_critical else ""
            lines.append(
                f"| {date_str} | {event.description} | "
                f"{event.event_type.value} | {critical} |"
            )
        
        return "\n".join(lines)


class DurationInfo(BaseModel):
    """Información de duración extraída."""
    
    value: float = Field(description="Valor numérico de la duración.")
    unit: str = Field(description="Unidad: days, weeks, months, years.")
    original_text: str = Field(description="Texto original.")
    
    def to_days(self) -> int:
        """Convierte la duración a días."""
        multipliers = {
            "days": 1,
            "weeks": 7,
            "months": 30,
            "years": 365,
        }
        return int(self.value * multipliers.get(self.unit, 1))


# Custom Exceptions

class TimelineExtractorError(Exception):
    """Excepción base para errores del extractor."""
    pass


class InvalidAnchorDateError(TimelineExtractorError):
    """La fecha anchor es inválida."""
    def __init__(self, anchor: str):
        self.anchor = anchor
        super().__init__(
            f"Fecha anchor inválida: '{anchor}'. "
            f"Use formato YYYY-MM-DD."
        )


class CircularDependencyError(TimelineExtractorError):
    """Se detectaron dependencias circulares."""
    def __init__(self, events: List[str]):
        self.events = events
        super().__init__(
            f"Dependencia circular detectada entre: {', '.join(events)}"
        )


class DateParserNotAvailableError(TimelineExtractorError):
    """dateparser no está instalado."""
    def __init__(self):
        super().__init__(
            "dateparser is required. Install with: pip install dateparser"
        )
