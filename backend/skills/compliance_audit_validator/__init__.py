"""
Compliance Audit Validator Skill

LLM-powered requirement compliance auditing for TenderCortex.
Implements traffic light protocol with gap analysis.
"""

from .definition import (
    AuditResult,
    BatchAuditResult,
    ComplianceCheckInput,
    ComplianceStatus,
    ComplianceValidatorError,
    InsufficientContextError,
    LLMServiceError,
    ParseResponseError,
    RequirementCategory,
    SeverityLevel,
)

from .impl import (
    ComplianceAuditValidator,
    audit_requirement,
    AUDITOR_SYSTEM_PROMPT,
)

__all__ = [
    # Classes
    "ComplianceAuditValidator",
    # Models
    "AuditResult",
    "BatchAuditResult",
    "ComplianceCheckInput",
    "ComplianceStatus",
    "RequirementCategory",
    "SeverityLevel",
    # Exceptions
    "ComplianceValidatorError",
    "InsufficientContextError",
    "LLMServiceError",
    "ParseResponseError",
    # Functions
    "audit_requirement",
    # Constants
    "AUDITOR_SYSTEM_PROMPT",
]
