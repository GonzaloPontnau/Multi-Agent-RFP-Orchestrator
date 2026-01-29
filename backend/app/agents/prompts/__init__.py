"""
Prompts module initialization.

This module exports all prompt-related constants and functions for use
by the specialist agents and router components.
"""

from app.agents.prompts.specialist_prompts import (
    # Domain configuration
    AVAILABLE_DOMAINS,
    DomainType,
    # Prompts
    RESPONSE_FORMAT_TEMPLATE,
    ROUTER_PROMPT,
    LEGAL_PROMPT,
    TECHNICAL_PROMPT,
    FINANCIAL_PROMPT,
    TIMELINE_PROMPT,
    REQUIREMENTS_PROMPT,
    GENERAL_PROMPT,
    QUANTITATIVE_PROMPT,
    SPECIALIST_PROMPTS,
    # Helper functions
    get_specialist_prompt,
    get_full_prompt,
    is_valid_domain,
)

__all__ = [
    # Domain configuration
    "AVAILABLE_DOMAINS",
    "DomainType",
    # Prompts
    "RESPONSE_FORMAT_TEMPLATE",
    "ROUTER_PROMPT",
    "LEGAL_PROMPT",
    "TECHNICAL_PROMPT",
    "FINANCIAL_PROMPT",
    "TIMELINE_PROMPT",
    "REQUIREMENTS_PROMPT",
    "GENERAL_PROMPT",
    "QUANTITATIVE_PROMPT",
    "SPECIALIST_PROMPTS",
    # Helper functions
    "get_specialist_prompt",
    "get_full_prompt",
    "is_valid_domain",
]
