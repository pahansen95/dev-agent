"""
Version-related type definitions for Knowledge Base Generator.

Centralizes type definitions related to versioning, patches, and version control.
"""

from typing import TypedDict, List, Dict, Optional


class Version(TypedDict):
    """Type for version information."""
    major: int
    minor: int
    patch: int


class PatchInfo(TypedDict):
    """Information about a patch."""
    version: str
    description: str
    timestamp: str
    changes_count: int