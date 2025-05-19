"""
Content-related type definitions for Knowledge Base Generator.

This module centralizes type definitions related to content management,
including changes, guidance, and generation parameters.
"""

from enum import Enum, auto
from typing import TypedDict, Dict, List, Optional


class ChangeType(Enum):
    """Types of content changes."""
    ADD = auto()
    REMOVE = auto()
    REPLACE = auto()
    SKIP = auto()  # No modification needed


class Change(TypedDict):
    """Represents a single content change."""
    type: str  # "ADD", "REMOVE", "REPLACE", or "SKIP"
    location: str  # Section title or identifier
    content: str  # The content being added, removed, or used as replacement


class GuidanceParameters(TypedDict):
    """Configurable parameters for content generation guidance."""
    style: str  # Article style (technical, conversational, etc.)
    audience: str  # Target audience description
    structure: str  # Desired article structure
    formatting: str  # Formatting preferences
    constraints: str  # Content constraints or filters


class ContentGenerationConfig(TypedDict):
    """Configuration for content generation."""
    template_name: str
    guidance_name: str
    max_tokens: int
    temperature: float