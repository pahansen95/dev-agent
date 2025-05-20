"""
Version-related type definitions for Knowledge Base Generator.

Centralizes type definitions related to versioning, patches, and version control.
"""

from dataclasses import dataclass

@dataclass
class Version:
    """Type for version information."""
    major: int
    minor: int
    patch: int

@dataclass
class PatchInfo:
    """Information about a patch."""
    version: str
    description: str
    timestamp: str
    changes_count: int
