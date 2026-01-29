"""
Base agents module initialization.

This module exports the base classes and protocols for building
specialist agents with dependency injection support.
"""

from app.agents.base.base_agent import (
    BaseSpecialistAgent,
    LLMProtocol,
    LoggerProtocol,
)

__all__ = [
    "BaseSpecialistAgent",
    "LLMProtocol",
    "LoggerProtocol",
]
