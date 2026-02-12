"""
Gantt Timeline Extractor - Implementation

Extracts and normalizes dates from RFP documents.
Features:
- Absolute date parsing with dateparser
- Relative date resolution
- Event type classification
- Dependency detection
- Duration extraction

Author: TenderCortex Team
"""

import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    import dateparser
    from dateparser.search import search_dates
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False

try:
    from .definition import (
        CircularDependencyError,
        DateParserNotAvailableError,
        DurationInfo,
        EventType,
        InvalidAnchorDateError,
        TimelineEvent,
        TimelineExtractorError,
        TimelineOutput,
    )
except ImportError:
    from definition import (
        CircularDependencyError,
        DateParserNotAvailableError,
        DurationInfo,
        EventType,
        InvalidAnchorDateError,
        TimelineEvent,
        TimelineExtractorError,
        TimelineOutput,
    )

logger = logging.getLogger(__name__)


# Keywords for event type classification
EVENT_KEYWORDS: Dict[EventType, List[str]] = {
    EventType.SUBMISSION_DEADLINE: [
        "entrega", "límite", "limite", "deadline", "vencimiento",
        "presentación", "presentacion", "oferta", "propuesta",
        "fecha límite", "fecha limite", "submission", "due date",
        "plazo de entrega", "cierre de recepción",
    ],
    EventType.QA_DEADLINE: [
        "consultas", "preguntas", "q&a", "aclaraciones", "dudas",
        "questions", "queries", "rfi", "clarifications",
        "fecha de consultas", "periodo de preguntas",
    ],
    EventType.PROJECT_START: [
        "inicio", "comienza", "firma", "adjudicación", "adjudicacion",
        "arranque", "kickoff", "kick-off", "start", "beginning",
        "apertura", "suscripción", "suscripcion", "award",
    ],
    EventType.CONTRACT_END: [
        "fin", "término", "termino", "vencimiento del contrato",
        "vigencia", "end", "termination", "expiry", "finalización",
        "finalizacion", "conclusión", "conclusion",
    ],
    EventType.MEETING: [
        "reunión", "reunion", "visita", "junta", "meeting",
        "site visit", "conferencia", "sesión", "sesion",
        "cita", "encuentro", "briefing",
    ],
    EventType.MILESTONE: [
        "fase", "etapa", "entregable", "hito", "milestone",
        "phase", "stage", "deliverable", "sprint", "iteración",
    ],
    EventType.PAYMENT: [
        "pago", "factura", "payment", "invoice", "cobro",
        "abono", "desembolso",
    ],
}

# Relative date patterns
RELATIVE_PATTERNS = [
    # Spanish
    (r'(\d+)\s*días?\s*(?:después|despues|post|tras|luego)\s*(?:de|del)?\s*(.+)', "days_after"),
    (r'(\d+)\s*días?\s*(?:antes)\s*(?:de|del)?\s*(.+)', "days_before"),
    (r'(\d+)\s*semanas?\s*(?:después|despues|post|tras|luego)\s*(?:de|del)?\s*(.+)', "weeks_after"),
    (r'(\d+)\s*semanas?\s*(?:antes)\s*(?:de|del)?\s*(.+)', "weeks_before"),
    (r'(\d+)\s*meses?\s*(?:después|despues|post|tras|luego)\s*(?:de|del)?\s*(.+)', "months_after"),
    (r'al?\s*(?:los)?\s*(\d+)\s*días?\s*(?:de|del)\s*(.+)', "days_after"),
    # English
    (r'(\d+)\s*days?\s*(?:after|from|post)\s*(.+)', "days_after"),
    (r'(\d+)\s*days?\s*(?:before|prior to)\s*(.+)', "days_before"),
    (r'(\d+)\s*weeks?\s*(?:after|from|post)\s*(.+)', "weeks_after"),
    (r'(\d+)\s*weeks?\s*(?:before|prior to)\s*(.+)', "weeks_before"),
]

# Duration patterns
DURATION_PATTERNS = [
    (r'duraci[oó]n\s*(?:de|del|:)?\s*(\d+)\s*(días|dias|semanas|meses|años|anos)', "es"),
    (r'(?:durar[aá]|vigencia\s*(?:de)?)\s*(\d+)\s*(días|dias|semanas|meses|años|anos)', "es"),
    (r'(\d+)\s*(días|dias|semanas|meses|años|anos)\s*(?:de\s*(?:duración|vigencia))', "es"),
    (r'duration\s*(?:of|:)?\s*(\d+)\s*(days|weeks|months|years)', "en"),
    (r'(\d+)\s*(days|weeks|months|years)\s*(?:duration|term)', "en"),
]

# Unit normalization
UNIT_MAP = {
    "día": "days", "días": "days", "dia": "days", "dias": "days", "day": "days", "days": "days",
    "semana": "weeks", "semanas": "weeks", "week": "weeks", "weeks": "weeks",
    "mes": "months", "meses": "months", "month": "months", "months": "months",
    "año": "years", "años": "years", "ano": "years", "anos": "years", "year": "years", "years": "years",
}


class GanttTimelineExtractor:
    """
    Extracts and normalizes timeline events from RFP documents.
    
    Handles absolute dates, relative expressions, and durations.
    Classifies events by type and detects dependencies.
    
    Usage:
        extractor = GanttTimelineExtractor()
        result = extractor.extract(
            text_chunks=[...],
            anchor_date="2024-04-01"
        )
        
        for event in result.events:
            print(f"{event.date_iso}: {event.description}")
    
    Raises:
        InvalidAnchorDateError: If anchor date format is invalid
        DateParserNotAvailableError: If dateparser is not installed
    """
    
    def __init__(self, language_hint: str = "es"):
        """
        Initialize the Timeline Extractor.
        
        Args:
            language_hint: Preferred language for parsing ("es", "en", or None for auto)
        """
        if not DATEPARSER_AVAILABLE:
            raise DateParserNotAvailableError()
        
        self.language_hint = language_hint
        self.dateparser_settings = {
            "PREFER_DATES_FROM": "future",
            "PREFER_DAY_OF_MONTH": "first",
            "RETURN_AS_TIMEZONE_AWARE": False,
        }
        if language_hint:
            self.dateparser_settings["PREFER_LOCALE_DATE_ORDER"] = True
    
    def extract(
        self,
        text_chunks: List[Any],  # List of DocumentChunk or dicts
        anchor_date: str,
        include_low_confidence: bool = False,
    ) -> TimelineOutput:
        """
        Extract timeline events from document chunks.
        
        Args:
            text_chunks: List of document chunks with content and metadata.
            anchor_date: Reference date for relative calculations (YYYY-MM-DD).
            include_low_confidence: Include events with low confidence.
        
        Returns:
            TimelineOutput with all extracted events.
        
        Raises:
            InvalidAnchorDateError: If anchor date is invalid.
        """
        # Validate anchor date
        try:
            anchor = datetime.strptime(anchor_date, "%Y-%m-%d").date()
        except ValueError:
            raise InvalidAnchorDateError(anchor_date)
        
        logger.info(f"Extracting timeline with anchor date: {anchor_date}")
        
        events: List[TimelineEvent] = []
        durations: List[DurationInfo] = []
        warnings: List[str] = []
        
        for chunk in text_chunks:
            # Handle both dict and object
            if isinstance(chunk, dict):
                content = chunk.get("content", "")
                page = chunk.get("page_number", 1)
                source = chunk.get("source_file", "unknown")
            else:
                content = getattr(chunk, "content", str(chunk))
                page = getattr(chunk, "page_number", 1)
                source = getattr(chunk, "source_file", "unknown")
            
            # Extract absolute dates
            abs_events = self._extract_absolute_dates(content, page, source, anchor)
            events.extend(abs_events)
            
            # Extract relative dates
            rel_events = self._extract_relative_dates(content, page, source)
            events.extend(rel_events)
            
            # Extract durations
            dur_info = self._extract_durations(content)
            durations.extend(dur_info)
        
        # Classify events by type
        for event in events:
            if event.event_type == EventType.OTHER:
                event.event_type = self._classify_event(event.original_text, event.description)
        
        # Mark critical deadlines
        for event in events:
            if event.event_type in (EventType.SUBMISSION_DEADLINE, EventType.QA_DEADLINE):
                event.is_critical = True
        
        # Resolve relative dates where possible
        events = self._resolve_relative_dates(events, anchor, warnings)
        
        # Filter low confidence if requested
        if not include_low_confidence:
            events = [e for e in events if e.confidence >= 0.5]
        
        # Sort chronologically (TBD at the end)
        events.sort(key=lambda e: (e.date_iso is None, e.date_iso or "9999-12-31"))
        
        # Calculate project duration
        duration_months = None
        duration_days = None
        if durations:
            # Use the longest duration found
            max_dur = max(durations, key=lambda d: d.to_days())
            duration_days = max_dur.to_days()
            duration_months = round(duration_days / 30, 1)
        
        # Extract critical deadlines and unresolved
        critical = [e for e in events if e.is_critical]
        unresolved = [e for e in events if e.date_iso is None]
        
        if unresolved:
            warnings.append(
                f"{len(unresolved)} evento(s) con fecha no resuelta (TBD)"
            )
        
        logger.info(f"Extracted {len(events)} events, {len(critical)} critical")
        
        return TimelineOutput(
            events=events,
            anchor_date_used=anchor_date,
            project_duration_months=duration_months,
            project_duration_days=duration_days,
            critical_deadlines=critical,
            unresolved_events=unresolved,
            warnings=warnings,
            total_events=len(events),
        )
    
    def _extract_absolute_dates(
        self,
        text: str,
        page: int,
        source: str,
        anchor: date,
    ) -> List[TimelineEvent]:
        """Extract absolute dates using dateparser."""
        events = []
        
        # Use dateparser.search to find all dates
        languages = [self.language_hint] if self.language_hint else None
        found_dates = search_dates(
            text,
            languages=languages,
            settings=self.dateparser_settings,
        )
        
        if not found_dates:
            return events
        
        for original_text, parsed_date in found_dates:
            # Skip very short matches (likely false positives)
            if len(original_text) < 4:
                continue
            
            # Check if year was missing and infer it
            year_inferred = False
            if not re.search(r'\b\d{4}\b', original_text):
                year_inferred = True
                # Adjust year if date has passed
                if parsed_date.date() < anchor:
                    parsed_date = parsed_date.replace(year=parsed_date.year + 1)
            
            # Get surrounding context for description
            context = self._get_context(text, original_text)
            description = self._generate_description(original_text, context)
            
            event = TimelineEvent(
                date_iso=parsed_date.strftime("%Y-%m-%d"),
                original_text=original_text,
                description=description,
                event_type=EventType.OTHER,  # Will be classified later
                is_relative=False,
                source_page=page,
                source_file=source,
                confidence=0.7 if year_inferred else 0.9,
            )
            events.append(event)
            
        return events
    
    def _extract_relative_dates(
        self,
        text: str,
        page: int,
        source: str,
    ) -> List[TimelineEvent]:
        """Extract relative date expressions."""
        events = []
        text_lower = text.lower()
        
        for pattern, offset_type in RELATIVE_PATTERNS:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            
            for match in matches:
                value = int(match.group(1))
                dependency = match.group(2).strip() if len(match.groups()) > 1 else None
                
                # Calculate offset in days
                if "weeks" in offset_type:
                    offset_days = value * 7
                elif "months" in offset_type:
                    offset_days = value * 30
                else:
                    offset_days = value
                
                # Negative if "before"
                if "before" in offset_type:
                    offset_days = -offset_days
                
                original_text = match.group(0)
                context = self._get_context(text, original_text)
                description = self._generate_description(original_text, context)
                
                event = TimelineEvent(
                    date_iso=None,  # Will be resolved later
                    original_text=original_text,
                    description=description,
                    event_type=EventType.OTHER,
                    is_relative=True,
                    source_page=page,
                    source_file=source,
                    dependency=dependency,
                    offset_days=offset_days,
                    confidence=0.8,
                )
                events.append(event)
        
        return events
    
    def _extract_durations(self, text: str) -> List[DurationInfo]:
        """Extract duration expressions."""
        durations = []
        text_lower = text.lower()
        
        for pattern, lang in DURATION_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            
            for match in matches:
                value = float(match.group(1))
                unit_raw = match.group(2).lower()
                unit = UNIT_MAP.get(unit_raw, "days")
                
                durations.append(DurationInfo(
                    value=value,
                    unit=unit,
                    original_text=match.group(0),
                ))
        
        return durations
    
    def _classify_event(self, original_text: str, description: str) -> EventType:
        """Classify event based on keywords."""
        combined = f"{original_text} {description}".lower()
        
        # Check each event type's keywords
        scores: Dict[EventType, int] = {et: 0 for et in EventType}
        
        for event_type, keywords in EVENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in combined:
                    scores[event_type] += 1
        
        # Return the highest scoring type
        max_type = max(scores, key=scores.get)
        return max_type if scores[max_type] > 0 else EventType.OTHER
    
    def _resolve_relative_dates(
        self,
        events: List[TimelineEvent],
        anchor: date,
        warnings: List[str],
    ) -> List[TimelineEvent]:
        """Resolve relative dates using anchor and dependencies."""
        resolved = []
        unresolved_map: Dict[str, TimelineEvent] = {}
        
        for event in events:
            if not event.is_relative or event.date_iso:
                resolved.append(event)
                continue
            
            # Try to resolve based on dependency
            if event.dependency and event.offset_days is not None:
                dep_lower = event.dependency.lower()
                
                # Check if dependency matches anchor keywords
                anchor_keywords = ["firma", "adjudicación", "adjudicacion", "contrato", "award", "signature"]
                if any(kw in dep_lower for kw in anchor_keywords):
                    # Use anchor date
                    resolved_date = anchor + timedelta(days=event.offset_days)
                    event.date_iso = resolved_date.strftime("%Y-%m-%d")
                    warnings.append(
                        f"Fecha relativa resuelta usando anchor: '{event.original_text}' -> {event.date_iso}"
                    )
                else:
                    # Check if we can find the dependency in resolved events
                    found = False
                    for res_event in resolved:
                        if res_event.date_iso and dep_lower in res_event.description.lower():
                            ref_date = datetime.strptime(res_event.date_iso, "%Y-%m-%d").date()
                            resolved_date = ref_date + timedelta(days=event.offset_days)
                            event.date_iso = resolved_date.strftime("%Y-%m-%d")
                            found = True
                            break
                    
                    if not found:
                        event.date_iso = None  # Keep as TBD
            
            resolved.append(event)
        
        return resolved
    
    def _get_context(self, text: str, target: str, window: int = 50) -> str:
        """Get surrounding context for a date match."""
        idx = text.lower().find(target.lower())
        if idx == -1:
            return ""
        
        start = max(0, idx - window)
        end = min(len(text), idx + len(target) + window)
        return text[start:end].strip()
    
    def _generate_description(self, original: str, context: str) -> str:
        """Generate a description based on context."""
        # Simple heuristic: look for action verbs near the date
        context_lower = context.lower()
        
        if any(kw in context_lower for kw in ["entrega", "presentación", "submission"]):
            return f"Fecha de entrega: {original}"
        elif any(kw in context_lower for kw in ["inicio", "start", "comienza"]):
            return f"Inicio: {original}"
        elif any(kw in context_lower for kw in ["fin", "término", "end"]):
            return f"Finalización: {original}"
        elif any(kw in context_lower for kw in ["reunión", "meeting", "visita"]):
            return f"Reunión/Visita: {original}"
        else:
            return f"Evento: {original}"


# Convenience function
def extract_timeline(
    text_chunks: List[Any],
    anchor_date: str,
) -> TimelineOutput:
    """
    Extract timeline with default settings.
    
    Convenience function for simple use cases.
    """
    extractor = GanttTimelineExtractor()
    return extractor.extract(text_chunks, anchor_date)
