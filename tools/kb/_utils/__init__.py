"""
Utilities package initialization for Knowledge Base Generator.

This package contains system and external utilities used throughout
the Knowledge Base Generator tool.
"""

# Import utility modules to make them available at the package level
from ._utils.filesystem import FileSystem
from ._utils.diff import DiffManager
from ._utils.llm import LLMService, AzureOpenAIService, MockLLMService