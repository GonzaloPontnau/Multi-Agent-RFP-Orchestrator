"""
Risk Score Calculator Skill

Deterministic bid viability scoring for TenderCortex.
Converts qualitative risk findings into quantitative metrics.
"""

from .definition import (
    CategoryBreakdown,
    EmptyRiskListError,
    InvalidRiskDataError,
    Recommendation,
    RiskAssessmentOutput,
    RiskCalculatorError,
    RiskCategory,
    RiskFactorInput,
    RiskMatrixCell,
    Severity,
)

from .impl import (
    RiskScoreCalculator,
    calculate_viability_score,
    SEVERITY_WEIGHTS,
    THRESHOLD_GO,
    THRESHOLD_REVIEW,
)

__all__ = [
    # Classes
    "RiskScoreCalculator",
    # Models
    "CategoryBreakdown",
    "Recommendation",
    "RiskAssessmentOutput",
    "RiskCategory",
    "RiskFactorInput",
    "RiskMatrixCell",
    "Severity",
    # Exceptions
    "EmptyRiskListError",
    "InvalidRiskDataError",
    "RiskCalculatorError",
    # Functions
    "calculate_viability_score",
    # Constants
    "SEVERITY_WEIGHTS",
    "THRESHOLD_GO",
    "THRESHOLD_REVIEW",
]
