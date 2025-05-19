"""
Type definitions for the Knowledge Base Generator.

This module defines TypedDict and other data structures used throughout the KB Generator tool.
"""

from enum import Enum, auto
from typing import TypedDict

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

class Version(TypedDict):
    """Type for version information."""
    major: int
    minor: int
    patch: int