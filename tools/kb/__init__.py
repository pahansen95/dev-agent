"""
# Knowledge Base Generator

A domain-agnostic tool for procedurally generating knowledge base documentation by
processing source material and applying intelligent content transformations.

## Overview

This application automatically transforms comprehensive reference material into
structured knowledge base articles through an iterative, LLM-assisted process. It analyzes source
content across multiple documents, determines optimal integration points, and creates structured
patches that progressively build a complete knowledge base.

Key capabilities:
- Multi-document processing with document-aware content organization
- Memory-efficient streaming for large file handling
- Markdown document parsing and hierarchical representation
- Intelligent content selection and integration
- Structured version control with diff-based patches
- LLM-powered content generation and refinement
- Deterministic and reproducible knowledge base creation

## Architectural Design

The application follows a layered architecture with clear boundaries:

1. **Document Processing Layer**
   - Parses multiple source documents into a unified tree structure
   - Maintains document boundaries and metadata
   - Manages document hierarchies and content extraction
   - Provides efficient document traversal mechanisms

2. **Content Management Layer**
   - Implements configurable templates and guidance for domain-agnostic content
   - Handles content generation through LLM integration
   - Implements versioning with structured patch management
   - Controls content transformations and diff generation

3. **Utilities Layer**
   - Provides cross-cutting functionality like LLM services
   - Handles file operations and streaming I/O
   - Implements diff management and patch handling
   - Ensures memory-efficient processing for large documents

4. **Application Layer**
   - Orchestrates document processing and content management
   - Provides streamlined CLI with flexible input handling
   - Manages configuration and processing directives
   - Controls overall workflow across multiple documents

Data flows through these layers in a single direction: the application layer coordinates
document processing to extract content from multiple sources, then uses content management
to generate knowledge base sections, finally utilizing utilities to persist results.

## Contributor Guidelines

### Coding Style

- **Python Version**: Requires Python 3.12+ for compatibility with typing features
- **Type Annotations**: Use comprehensive typing with optional static analysis
- **Documentation**: Every function, class, and module requires docstrings with:
  - Purpose description
  - Parameter documentation with types
  - Return value documentation
  - Exception documentation when applicable
- **Naming Conventions**:
  - Classes: `PascalCase`
  - Functions/methods: `snake_case`
  - Variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
  - Private methods/attributes: Prefix with underscore `_method_name`

### Structural Layout

- **Organization**: Group related functionality in namespaces (classes)
- **Modularity**: Maintain clear boundaries between layers
- **Import Order**:
  1. Future imports
  2. Standard library imports
  3. Third-party imports
  4. Local application imports
- **Code Formatting**: Custom Styling will be applied.

### Additional Directives

- **Error Handling**: Propagate exceptions to appropriate layers; avoid silent failures
- **Dependency Injection**: Use explicit dependency injection for testability
- **Interface Contracts**: Define clear protocols for cross-layer interactions
- **Maintainability**: Prioritize readability and clear intent over cleverness

When adding new functionality:
1. Identify the appropriate layer
2. Implement as a class or method within existing namespaces
3. Update interfaces as needed, maintaining backward compatibility
4. Add comprehensive docstrings and type annotations
5. Consider error cases and edge conditions

This architecture ensures separation of concerns while maintaining a cohesive application
that can evolve to handle diverse document sources and knowledge domains.
"""

# Version information
__version__ = "0.1.0"

# Initialize logging system early
from ._utils.logger import configure_logging, get_logger

# Get a logger for the main package
logger = get_logger(__name__)
logger.info(f"Knowledge Base Generator v{__version__} initializing")

# Import main modules for easier access
from .source import (Document, Node, Tree, MarkdownParser)

from .artifact import (PromptTemplate, TemplateManager, GuidanceManager, ContentGenerator, Patch, VersionManager)

# Import core components
from ._core import (ConfigurationError, TemplateError, GuidanceError, ContentGenerationError, ParsingError, Version, Change, GuidanceParameters)

# Import utility components
from ._utils import (FileSystem, DiffManager, LLMService, AzureOpenAIService, MockLLMService)

logger.debug("KB Generator package imports completed")
