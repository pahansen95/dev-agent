"""
# Knowledge Base

A domain-agnostic tool for managing a knowledge base.

## Overview

This application has features including:

- Iterative generation of well formed KB Artifacts from source documentation
- Parsing & Rendering of KB Artifacts

## Architectural Design

The application follows a layered architecture with clear boundaries:

1. **Artifact Layer**: Handling the iterative generation & rendering of KB artifacts.
2. **Core Layer**: Providing cross cutting functionality intrinsic to the App (e.g. The KB Artifact, CLI Interface & Core Types).
3. **Utilities Layer**: Providing cross cutting functionality extrinsic to the App (e.g. The OS & External Systems).

## Contributor Guidelines

### Coding Style

- **Python Version**: Requires Python 3.12+ for compatibility with typing features
- **Type Annotations**: Use comprehensive typing.
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

- **Organization**: Group related functionality in modules; breakout to sub-packages when individual modules become overloaded
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
- **Coding**: Be declarative; if imperative code is required then document it declaratively.

When adding new functionality:
1. Identify the appropriate layer
2. Implement as a class or method within an existing module or propose a new module/sub-package.
3. Add comprehensive docstrings and type annotations
4. Fail fast & handle minimal edge cases

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
