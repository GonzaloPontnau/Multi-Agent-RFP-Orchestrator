"""
Tech Stack Mapper Skill

Technology extraction and normalization for RFP analysis.
Maps variations to canonical names and categorizes by type.
"""

from .definition import (
    AmbiguousTechError,
    CompatibilityResult,
    EmptyInputError,
    RequirementLevel,
    TechCategory,
    TechEntity,
    TechMapperError,
    TechStackOutput,
)

from .impl import (
    TechStackMapper,
    extract_tech_stack,
    CANONICAL_MAP,
)

__all__ = [
    # Classes
    "TechStackMapper",
    # Models
    "CompatibilityResult",
    "RequirementLevel",
    "TechCategory",
    "TechEntity",
    "TechStackOutput",
    # Exceptions
    "AmbiguousTechError",
    "EmptyInputError",
    "TechMapperError",
    # Functions
    "extract_tech_stack",
    # Constants
    "CANONICAL_MAP",
]
