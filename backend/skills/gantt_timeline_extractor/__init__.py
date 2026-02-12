"""
Gantt Timeline Extractor Skill

Extracts and normalizes timeline events from RFP documents.
Handles absolute dates, relative expressions, and durations.
"""

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

from .impl import (
    GanttTimelineExtractor,
    extract_timeline,
    EVENT_KEYWORDS,
)

__all__ = [
    # Classes
    "GanttTimelineExtractor",
    # Models
    "DurationInfo",
    "EventType",
    "TimelineEvent",
    "TimelineOutput",
    # Exceptions
    "CircularDependencyError",
    "DateParserNotAvailableError",
    "InvalidAnchorDateError",
    "TimelineExtractorError",
    # Functions
    "extract_timeline",
    # Constants
    "EVENT_KEYWORDS",
]
