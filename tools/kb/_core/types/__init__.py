"""
Core type definitions for the Knowledge Base Generator.

This module centralizes type definitions to eliminate duplication and provide
a single source of truth for the entire codebase.
"""

# Re-export all types from submodules for easy access
from ._core.types.document import Document, DocumentNode, Node, Tree
from ._core.types.content import (
    Change, ChangeType, GuidanceParameters, ContentGenerationConfig
)
from ._core.types.version import Version, PatchInfo
from ._core.types.protocols import LLMService, FileSystemService

# Export specific enum values for convenience
from ._core.types.content import ChangeType
