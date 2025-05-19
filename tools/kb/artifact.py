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

from __future__ import annotations

import argparse
import difflib
import json
import os
import random
import re
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Protocol, Self, Tuple, TypedDict, Union, cast, Callable

# -----------------------------------------------------------------------------
# Document Processing Layer
# -----------------------------------------------------------------------------

class DocumentProcessing:

  """Namespace for document processing functionality."""

  class ParsingError(Exception):

    """Exception raised for errors during markdown parsing."""
    pass

  class Document:

    """Represents a document in the stream."""

    def __init__(self, name: str, content: str, size: int = 0) -> None:
      """
            Initialize a document.
            
            Args:
                name: Document name or identifier
                content: Document content
                size: Original document size in bytes (if known)
            """
      self.name = name
      self.content = content
      self.size = size if size > 0 else len(content.encode('utf-8'))

    def __repr__(self) -> str:
      """Return string representation of the document."""
      return f"Document(name='{self.name}', size={self.size} bytes)"

  class MarkdownStream:

    """Base class for markdown streams."""

    DOC_SEPARATOR_PATTERN = re.compile(r'<!-- DOC name="([^"]+)" size_of=(\d+) -->')

    def __init__(self) -> None:
      """Initialize the markdown stream."""
      self.content = "" # Full stream content
      self.documents: List[DocumentProcessing.Document] = []

    def read_all(self) -> str:
      """
            Read all content from the stream.
            
            Returns:
                The full content as a string
            """
      return self.content

    def get_documents(self) -> List["DocumentProcessing.Document"]:
      """
            Get all documents parsed from the stream.
            
            Returns:
                List of Document objects
            """
      return self.documents

    def _parse_document_separators(self, content: str) -> None:
      """
            Parse document separators in the stream content.
            
            Args:
                content: The stream content to parse
            """
      # Split content by document separators
      parts = self.DOC_SEPARATOR_PATTERN.split(content)

      # First part is either empty or content before the first separator
      current_content = parts[0].strip()

      # If there's content before the first separator, treat it as a default document
      if current_content:
        self.documents.append(DocumentProcessing.Document("default", current_content))

      # Process the remaining parts (name, size, content, name, size, content, ...)
      i = 1
      while i < len(parts) - 2:
        doc_name = parts[i]
        try:
          doc_size = int(parts[i + 1])
        except ValueError:
          doc_size = 0
        doc_content = parts[i + 2].strip()

        self.documents.append(DocumentProcessing.Document(doc_name, doc_content, doc_size))
        i += 3

  class FileMarkdownStream(MarkdownStream):

    """Implementation for reading markdown from one or more files."""

    def __init__(self, file_paths: List[str]) -> None:
      """
            Initialize a file-based markdown stream.
            
            Args:
                file_paths: List of paths to markdown files
                
            Raises:
                FileNotFoundError: If any file doesn't exist
                IOError: If there's an error reading a file
            """
      super().__init__()
      self.file_paths = file_paths
      self._load_files()

    def _load_files(self) -> None:
      """
            Load content from all files and parse document separators.
            
            Raises:
                FileNotFoundError: If any file doesn't exist
                IOError: If there's an error reading a file
            """
      # Read all files and concatenate content
      combined_content = []

      for file_path in self.file_paths:
        with open(file_path, 'r', encoding='utf-8') as f:
          file_content = f.read()
          file_size = len(file_content.encode('utf-8'))

        # Add document separator before file content
        separator = f'<!-- DOC name="{os.path.basename(file_path)}" size_of={file_size} -->'
        combined_content.append(separator)
        combined_content.append(file_content)

      # Store the combined content
      self.content = "\n\n".join(combined_content)

      # Parse document separators
      self._parse_document_separators(self.content)

  class StdinMarkdownStream(MarkdownStream):

    """Implementation for reading markdown from standard input."""

    def __init__(self, is_concat_stream: bool = False) -> None:
      """
            Initialize a stdin-based markdown stream.
            
            Args:
                is_concat_stream: Whether the input is already a concatenated stream
                                 with document separators
            """
      super().__init__()
      self.is_concat_stream = is_concat_stream
      self._load_from_stdin()

    def _load_from_stdin(self) -> None:
      """Load content from standard input and parse document separators."""
      # Read all content from stdin
      self.content = sys.stdin.read()

      # If not a concat stream, wrap in a document separator
      if not self.is_concat_stream:
        # Treat as a single document
        doc_size = len(self.content.encode('utf-8'))
        self.documents.append(DocumentProcessing.Document("stdin", self.content, doc_size))
      else:
        # Parse document separators
        self._parse_document_separators(self.content)

  class Node:

    """Represents a node in the markdown document tree."""

    def __init__(
        self,
        level: int,
        title: str,
        content: str = "",
        parent: Optional["DocumentProcessing.Node"] = None,
        document: Optional["DocumentProcessing.Document"] = None) -> None:
      """
            Initialize a node.
            
            Args:
                level: Header level (1 for #, 2 for ##, etc.)
                title: The node title
                content: The node content
                parent: Optional parent node
                document: Document this node belongs to
            """
      self.level: int = level # Header level (1 for #, 2 for ##, etc.)
      self.title: str = title.strip()
      self.content: str = content
      self.parent: Optional["DocumentProcessing.Node"] = parent
      self.children: List["DocumentProcessing.Node"] = []
      self.document: Optional["DocumentProcessing.Document"] = document

    def add_child(self, child: "DocumentProcessing.Node") -> None:
      """
            Add a child node to this node.
            
            Args:
                child: The child node to add
            """
      child.parent = self
      self.children.append(child)

    def add_content(self, content: str) -> None:
      """
            Append content to this node.
            
            Args:
                content: The content to append
            """
      if self.content:
        self.content += "\n" + content
      else:
        self.content = content

    def is_empty(self) -> bool:
      """
            Check if the node has no meaningful content.
            
            Returns:
                True if the node is empty, False otherwise
            """
      return not self.content.strip() and not self.children

    def __repr__(self) -> str:
      """
            Get a string representation of this node.
            
            Returns:
                A string representation of the node
            """
      doc_name = self.document.name if self.document else "N/A"
      return f"Node(level={self.level}, title='{self.title}', doc='{doc_name}', children={len(self.children)})"

  class Tree:

    """Represents a tree structure of a markdown document."""

    def __init__(self) -> None:
      """Initialize an empty document tree."""
      self.root: DocumentProcessing.Node = DocumentProcessing.Node(0, "ROOT")
      self.current: DocumentProcessing.Node = self.root
      # Map of document names to subtrees
      self.document_roots: Dict[str, DocumentProcessing.Node] = {}

    def add_node(self, level: int, title: str, content: str = "", document: Optional[DocumentProcessing.Document] = None) -> DocumentProcessing.Node:
      """
            Add a node to the tree at the appropriate level.
            
            Args:
                level: Header level (1 for #, 2 for ##, etc.)
                title: The node title
                content: The node content
                document: The document this node belongs to
                
            Returns:
                The newly created node
            """
      # Find the appropriate parent for this node
      parent: DocumentProcessing.Node = self.root
      node: DocumentProcessing.Node = self.root

      # If this is the first node for a document, create a document root
      if document and document.name not in self.document_roots:
        # Create a document root node
        doc_root = DocumentProcessing.Node(0, document.name, "", self.root, document)
        self.root.add_child(doc_root)
        self.document_roots[document.name] = doc_root
        parent = doc_root
        node = doc_root
      elif document and document.name in self.document_roots:
        # Use existing document root
        parent = self.document_roots[document.name]
        node = parent

      # Traverse up the tree until we find a node with a lower level
      while node.level >= level and node.parent is not None:
        node = node.parent

      parent = node

      # Create and add the new node
      new_node = DocumentProcessing.Node(level, title, content, parent, document)
      parent.add_child(new_node)
      self.current = new_node

      return new_node

    def add_content_to_current(self, content: str) -> None:
      """
            Add content to the current node.
            
            Args:
                content: The content to add
            """
      if self.current != self.root:
        self.current.add_content(content)

    def dfs_traversal(self) -> List[Tuple[DocumentProcessing.Node, int]]:
      """
            Perform a depth-first traversal of the tree, returning node and depth pairs.
            
            Returns:
                List of (node, depth) pairs
            """
      result: List[Tuple[DocumentProcessing.Node, int]] = []

      def _dfs(node: DocumentProcessing.Node, depth: int = 0) -> None:
        result.append((node, depth))
        for child in node.children:
          _dfs(child, depth + 1)

      _dfs(self.root)
      return result

    def get_nodes_by_document(self, document_name: str) -> List[DocumentProcessing.Node]:
      """
            Get all nodes belonging to a specific document.
            
            Args:
                document_name: Name of the document
                
            Returns:
                List of nodes in the document
            """
      if document_name not in self.document_roots:
        return []

      result = []
      doc_root = self.document_roots[document_name]

      def _collect_nodes(node: DocumentProcessing.Node) -> None:
        if node != doc_root: # Skip the document root itself
          result.append(node)
        for child in node.children:
          _collect_nodes(child)

      _collect_nodes(doc_root)
      return result

    def validate(self) -> List[str]:
      """
            Validate the tree structure and content.
            
            Returns:
                A list of validation warnings, empty if no issues found
            """
      warnings = []

      # Validate each node in the tree
      for node, depth in self.dfs_traversal():
        # Skip root node and document root nodes
        if node == self.root or node.level == 0:
          continue

        # Check for empty nodes
        if node.is_empty():
          warnings.append(f"Empty node found: '{node.title}'")

        # Check for invalid level jumps (e.g., h1 -> h3)
        if node.parent and node.parent.level > 0: # Skip root and doc roots
          if node.level > node.parent.level + 1:
            warnings.append(f"Header level jump from {node.parent.level} to {node.level} "
                            f"at node '{node.title}'")

      return warnings

  class MarkdownParser:

    """Parses markdown content into a tree structure."""

    HEADER_PATTERN = re.compile(r"^(#+)\s+(.+)$")

    @staticmethod
    def parse_stream(stream: DocumentProcessing.MarkdownStream) -> DocumentProcessing.Tree:
      """
            Parse a markdown stream into a tree structure.
            
            Args:
                stream: A markdown stream
                    
            Returns:
                A tree representation of the markdown structure
                    
            Raises:
                DocumentProcessing.ParsingError: If there's an error parsing the stream
            """
      tree = DocumentProcessing.Tree()

      # Process each document in the stream
      for document in stream.get_documents():
        DocumentProcessing.MarkdownParser._parse_document(document, tree)

      # Validate the tree
      warnings = tree.validate()
      if warnings:
        # Just log warnings but don't fail
        print("Markdown parsing warnings:")
        for warning in warnings:
          print(f"- {warning}")

      return tree

    @staticmethod
    def _parse_document(document: DocumentProcessing.Document, tree: DocumentProcessing.Tree) -> None:
      """
            Parse a single document and add it to the tree.
            
            Args:
                document: The document to parse
                tree: The tree to add nodes to
                
            Raises:
                DocumentProcessing.ParsingError: If there's an error parsing the document
            """
      lines = document.content.splitlines()
      current_node = None
      current_content: List[str] = []
      line_number = 0

      for line in lines:
        line_number += 1
        line = line.rstrip()
        header_match = DocumentProcessing.MarkdownParser.HEADER_PATTERN.match(line)

        if header_match:
          # If we have accumulated content, add it to the current node
          if current_content and current_node:
            current_node.content += "\n".join(current_content)
            current_content = []

          # Create a new node for this header
          level = len(header_match.group(1))
          title = header_match.group(2)

          # Check for empty title
          if not title.strip():
            raise DocumentProcessing.ParsingError(f"Empty header title at line {line_number} in document '{document.name}'")

          # Check for excessively deep header level
          if level > 6:
            raise DocumentProcessing.ParsingError(f"Header level too deep (level {level}) at line {line_number} in document '{document.name}': {line}")

          current_node = tree.add_node(level, title, "", document)
        else:
          # Add this line to the accumulated content
          current_content.append(line)

      # Add any remaining content to the last node
      if current_content and current_node:
        current_node.content += "\n".join(current_content)

    @staticmethod
    def parse_files(file_paths: List[str]) -> DocumentProcessing.Tree:
      """
            Parse multiple markdown files into a tree structure.
            
            Args:
                file_paths: List of paths to markdown files
                    
            Returns:
                A tree representation of the markdown files
                    
            Raises:
                DocumentProcessing.ParsingError: If there's an error parsing any file
            """
      stream = DocumentProcessing.FileMarkdownStream(file_paths)
      return DocumentProcessing.MarkdownParser.parse_stream(stream)

    @staticmethod
    def parse_stdin(is_concat_stream: bool = False) -> DocumentProcessing.Tree:
      """
            Parse markdown from standard input into a tree structure.
            
            Args:
                is_concat_stream: Whether the input is already a concatenated stream
                                 with document separators
                    
            Returns:
                A tree representation of the markdown from stdin
                    
            Raises:
                DocumentProcessing.ParsingError: If there's an error parsing the input
            """
      stream = DocumentProcessing.StdinMarkdownStream(is_concat_stream)
      return DocumentProcessing.MarkdownParser.parse_stream(stream)

# -----------------------------------------------------------------------------
# Content Management Layer
# -----------------------------------------------------------------------------

class ContentManagement:

  """Namespace for content management functionality."""

  class ChangeType(Enum):

    """Types of content changes."""
    ADD = auto()
    REMOVE = auto()
    REPLACE = auto()
    SKIP = auto() # No modification needed

  class Change(TypedDict):

    """Represents a single content change."""
    type: str # "ADD", "REMOVE", "REPLACE", or "SKIP"
    location: str # Section title or identifier
    content: str # The content being added, removed, or used as replacement

  class GuidanceParameters(TypedDict):

    """Configurable parameters for content generation guidance."""
    style: str # Article style (technical, conversational, etc.)
    audience: str # Target audience description
    structure: str # Desired article structure
    formatting: str # Formatting preferences
    constraints: str # Content constraints or filters

  class TemplateError(Exception):

    """Exception raised for errors with prompt templates."""
    pass

  class GuidanceError(Exception):

    """Exception raised for errors with guidance parameters."""
    pass

  class ContentGenerationError(Exception):

    """Exception raised for errors during content generation."""
    pass

  class Version(TypedDict):

    """Type for version information."""
    major: int
    minor: int
    patch: int

  @dataclass
  class PromptTemplate:

    """Template for generating system and user prompts for content generation."""

    system_template: str
    """Template string for system prompt with placeholders"""

    user_template: str
    """Template string for user prompt with placeholders"""

    def format_system_prompt(self, **kwargs) -> str:
      """
            Format the system prompt template with provided values.
            
            Args:
                **kwargs: Key-value pairs to substitute in the template
                
            Returns:
                Formatted system prompt
                
            Raises:
                ContentManagement.TemplateError: If formatting fails
            """
      try:
        return self.system_template.format(**kwargs)
      except KeyError as e:
        raise ContentManagement.TemplateError(f"Missing parameter for system template: {e}")
      except Exception as e:
        raise ContentManagement.TemplateError(f"Error formatting system template: {e}")

    def format_user_prompt(self, **kwargs) -> str:
      """
            Format the user prompt template with provided values.
            
            Args:
                **kwargs: Key-value pairs to substitute in the template
                
            Returns:
                Formatted user prompt
                
            Raises:
                ContentManagement.TemplateError: If formatting fails
            """
      try:
        return self.user_template.format(**kwargs)
      except KeyError as e:
        raise ContentManagement.TemplateError(f"Missing parameter for user template: {e}")
      except Exception as e:
        raise ContentManagement.TemplateError(f"Error formatting user template: {e}")

  class TemplateManager:

    """Manages prompt templates for content generation."""

    # Default templates for knowledge base article generation
    DEFAULT_SYSTEM_TEMPLATE = """
You are an expert technical writer helping to create a knowledge base article.
Your task is to analyze source content and integrate it into the current article.

The guidance for authoring includes:
- Style: {style}
- Target audience: {audience}
- Article structure: {structure}
- Formatting preferences: {formatting}
- Content constraints: {constraints}
"""

    DEFAULT_USER_TEMPLATE = """
I'm working on a section of the article titled "{section_title}".

Here's the source content:
```
{source_content}
```

Here's the current article:
```
{current_article}
```

Your task is to analyze the source content and determine if it should be integrated into the article. You have four options:
1. ADD new content at an appropriate location in the article
2. REMOVE existing content that is outdated or redundant
3. REPLACE existing content with improved content
4. SKIP if the source content is already adequately covered in the article or isn't relevant

Please analyze the current article and the source content, then provide:
1. A brief description of your decision (one line)
2. If not skipping, the complete updated article with your changes integrated
3. A list of specific changes you made, each formatted as:
   - Operation (ADD, REMOVE, REPLACE, or SKIP)
   - Location (section title or paragraph that helps identify where the change occurs)
   - Content (the actual text being added, removed, or used as replacement; omit for SKIP)

Focus on maintaining a cohesive, well-structured document that clearly explains concepts.
You should choose SKIP if the content is:
- Already adequately covered in the article
- Too advanced for this article
- Not directly relevant to the topic
- Better suited for a different section that will be handled separately
"""

    def __init__(self) -> None:
      """Initialize the template manager with default templates."""
      self.templates: Dict[str, ContentManagement.PromptTemplate] = {
        "default": ContentManagement.PromptTemplate(system_template=self.DEFAULT_SYSTEM_TEMPLATE, user_template=self.DEFAULT_USER_TEMPLATE)
      }

    def add_template(self, name: str, system_template: str, user_template: str) -> None:
      """
            Add a new prompt template.
            
            Args:
                name: Template identifier
                system_template: System prompt template
                user_template: User prompt template
                
            Raises:
                ContentManagement.TemplateError: If the template name already exists
            """
      if name in self.templates:
        raise ContentManagement.TemplateError(f"Template '{name}' already exists")

      self.templates[name] = ContentManagement.PromptTemplate(system_template=system_template, user_template=user_template)

    def get_template(self, name: str = "default") -> ContentManagement.PromptTemplate:
      """
            Get a prompt template by name.
            
            Args:
                name: Template identifier
                
            Returns:
                The requested template
                
            Raises:
                ContentManagement.TemplateError: If the template name doesn't exist
            """
      if name not in self.templates:
        raise ContentManagement.TemplateError(f"Template '{name}' not found")
      return self.templates[name]

    def load_template_file(self, filepath: str) -> List[str]:
      """
            Load templates from a JSON file.
            
            Expected format:
            ```json
            {
                "template_name": {
                    "system_template": "...",
                    "user_template": "..."
                },
                ...
            }
            ```
            
            Args:
                filepath: Path to the template file
                
            Returns:
                List of loaded template names
                
            Raises:
                ContentManagement.TemplateError: If there's an error loading templates
            """
      try:
        with open(filepath, 'r', encoding='utf-8') as f:
          templates_data = json.load(f)

        loaded_templates = []
        for name, template_data in templates_data.items():
          if not isinstance(template_data, dict):
            raise ContentManagement.TemplateError(f"Invalid template data for '{name}'")

          system_template = template_data.get("system_template")
          user_template = template_data.get("user_template")

          if not system_template or not user_template:
            raise ContentManagement.TemplateError(f"Missing template content for '{name}'")

          self.add_template(name, system_template, user_template)
          loaded_templates.append(name)

        return loaded_templates

      except json.JSONDecodeError:
        raise ContentManagement.TemplateError(f"Invalid JSON format in template file: {filepath}")
      except Exception as e:
        if not isinstance(e, ContentManagement.TemplateError):
          raise ContentManagement.TemplateError(f"Error loading template file: {str(e)}")
        raise

  class GuidanceManager:

    """Manages guidance parameters for content generation."""

    # Default guidance parameters
    DEFAULT_GUIDANCE = {
      "style": "Clear, concise, and technical",
      "audience": "Technical professionals with domain knowledge",
      "structure": "Hierarchical with clear headings and logical flow",
      "formatting": "Use markdown formatting with code blocks where appropriate",
      "constraints": "Focus on practical, actionable information"
    }

    def __init__(self) -> None:
      """Initialize the guidance manager with default parameters."""
      self.guidance: Dict[str, Dict[str, str]] = {"default": self.DEFAULT_GUIDANCE.copy()}

    def add_guidance(self, name: str, parameters: Dict[str, str]) -> None:
      """
            Add a new set of guidance parameters.
            
            Args:
                name: Guidance identifier
                parameters: Guidance parameter values
                
            Raises:
                ContentManagement.GuidanceError: If the guidance name already exists
            """
      if name in self.guidance:
        raise ContentManagement.GuidanceError(f"Guidance '{name}' already exists")

      # Ensure all required parameters are present
      for key in self.DEFAULT_GUIDANCE:
        if key not in parameters:
          parameters[key] = self.DEFAULT_GUIDANCE[key]

      self.guidance[name] = parameters

    def get_guidance(self, name: str = "default") -> Dict[str, str]:
      """
            Get guidance parameters by name.
            
            Args:
                name: Guidance identifier
                
            Returns:
                The requested guidance parameters
                
            Raises:
                ContentManagement.GuidanceError: If the guidance name doesn't exist
            """
      if name not in self.guidance:
        raise ContentManagement.GuidanceError(f"Guidance '{name}' not found")
      return self.guidance[name]

    def load_guidance_file(self, filepath: str) -> List[str]:
      """
            Load guidance parameters from a JSON file.
            
            Expected format:
            ```json
            {
                "guidance_name": {
                    "style": "...",
                    "audience": "...",
                    "structure": "...",
                    "formatting": "...",
                    "constraints": "..."
                },
                ...
            }
            ```
            
            Args:
                filepath: Path to the guidance file
                
            Returns:
                List of loaded guidance names
                
            Raises:
                ContentManagement.GuidanceError: If there's an error loading guidance
            """
      try:
        with open(filepath, 'r', encoding='utf-8') as f:
          guidance_data = json.load(f)

        loaded_guidance = []
        for name, parameters in guidance_data.items():
          if not isinstance(parameters, dict):
            raise ContentManagement.GuidanceError(f"Invalid guidance data for '{name}'")

          self.add_guidance(name, parameters)
          loaded_guidance.append(name)

        return loaded_guidance

      except json.JSONDecodeError:
        raise ContentManagement.GuidanceError(f"Invalid JSON format in guidance file: {filepath}")
      except Exception as e:
        if not isinstance(e, ContentManagement.GuidanceError):
          raise ContentManagement.GuidanceError(f"Error loading guidance file: {str(e)}")
        raise

  class ContentSelector:

    """Selects content from source nodes based on configured rules."""

    def __init__(self) -> None:
      """Initialize the content selector with no rules."""
      self.rules: List[ContentManagement.ContentSelectionRule] = []

    def add_rule(self, rule: "ContentManagement.ContentSelectionRule") -> None:
      """
            Add a content selection rule.
            
            Args:
                rule: The rule to add
            """
      self.rules.append(rule)
      # Sort rules by priority (descending)
      self.rules.sort(key=lambda r: r.priority, reverse=True)

    def should_include(self, node: DocumentProcessing.Node) -> bool:
      """
            Determine if a node should be included in the article.
            
            Rules are evaluated in priority order. The first rule that applies
            determines the result.
            
            Args:
                node: The node to evaluate
                
            Returns:
                True if the node should be included, False otherwise
            """
      for rule in self.rules:
        if rule.applies_to(node):
          return True

      # Default to inclusion if no rules match
      return True

    def filter_nodes(self, nodes: List[DocumentProcessing.Node]) -> List[DocumentProcessing.Node]:
      """
            Filter a list of nodes based on the configured rules.
            
            Args:
                nodes: List of nodes to filter
                
            Returns:
                List of nodes that should be included
            """
      return [node for node in nodes if self.should_include(node)]

  class ContentSelectionRule:

    """Defines a rule for selecting content to include in the article."""

    def __init__(self, name: str, condition: Callable[[DocumentProcessing.Node], bool], priority: int = 0) -> None:
      """
            Initialize a content selection rule.
            
            Args:
                name: Rule identifier
                condition: Function that evaluates whether to include a node
                priority: Rule priority (higher values take precedence)
            """
      self.name = name
      self.condition = condition
      self.priority = priority

    def applies_to(self, node: DocumentProcessing.Node) -> bool:
      """
            Check if this rule applies to a node.
            
            Args:
                node: The node to evaluate
                
            Returns:
                True if the rule applies, False otherwise
            """
      return self.condition(node)

  @staticmethod
  def create_header_level_rule(max_level: int) -> "ContentManagement.ContentSelectionRule":
    """
        Create a rule that includes nodes up to a specified header level.
        
        Args:
            max_level: Maximum header level to include (1-6)
            
        Returns:
            ContentManagement.ContentSelectionRule that includes nodes with level <= max_level
        """
    return ContentManagement.ContentSelectionRule(name=f"header_level_max_{max_level}", condition=lambda node: node.level <= max_level, priority=100)

  @staticmethod
  def create_keyword_rule(keywords: List[str], case_sensitive: bool = False) -> "ContentManagement.ContentSelectionRule":
    """
        Create a rule that includes nodes containing specified keywords.
        
        Args:
            keywords: List of keywords to match
            case_sensitive: Whether to use case-sensitive matching
            
        Returns:
            ContentManagement.ContentSelectionRule that includes nodes with matching keywords
        """

    def has_keywords(node: DocumentProcessing.Node) -> bool:
      text = node.title + "\n" + node.content
      for keyword in keywords:
        if case_sensitive:
          if keyword in text:
            return True
        else:
          if keyword.lower() in text.lower():
            return True
      return False

    return ContentManagement.ContentSelectionRule(name=f"keywords_{','.join(keywords)}", condition=has_keywords, priority=50)

  @staticmethod
  def create_regex_rule(pattern: str) -> "ContentManagement.ContentSelectionRule":
    """
        Create a rule that includes nodes matching a regex pattern.
        
        Args:
            pattern: Regular expression pattern to match
            
        Returns:
            ContentManagement.ContentSelectionRule that includes nodes matching the pattern
        """
    regex = re.compile(pattern)

    def matches_pattern(node: DocumentProcessing.Node) -> bool:
      text = node.title + "\n" + node.content
      return bool(regex.search(text))

    return ContentManagement.ContentSelectionRule(name=f"regex_{pattern}", condition=matches_pattern, priority=75)

  class SimpleContextWindowManager:

    """
        Manages context window size constraints for large content sections.
        
        This class helps ensure that content being processed fits within
        LLM context window limitations by intelligently splitting and
        recombining content as needed.
        """

    def __init__(self, max_tokens_per_window: int = 4000) -> None:
      """
            Initialize the context window manager.
            
            Args:
                max_tokens_per_window: Maximum tokens allowed per context window
            """
      self.max_tokens_per_window = max_tokens_per_window
      # Very rough approximation: 1 token ≈ 4 characters for English text
      self.chars_per_token = 4

    def _estimate_token_count(self, text: str) -> int:
      """
            Estimate the number of tokens in a text.
            
            This is a very rough approximation. In a production system,
            you would want to use a proper tokenizer.
            
            Args:
                text: The text to estimate tokens for
                
            Returns:
                Estimated token count
            """
      return len(text) // self.chars_per_token

    def split_content(self, content: str) -> List[str]:
      """
            Split content into chunks that fit within context window.
            
            Args:
                content: The content to split
                
            Returns:
                List of content chunks
            """
      if self._estimate_token_count(content) <= self.max_tokens_per_window:
        return [content]

      # Split by paragraphs first
      paragraphs = content.split("\n\n")
      chunks = []
      current_chunk = ""

      for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit
        if self._estimate_token_count(current_chunk + paragraph) > self.max_tokens_per_window:
          # If the current chunk is not empty, add it to chunks
          if current_chunk:
            chunks.append(current_chunk)
            current_chunk = ""

          # If the paragraph itself is too large, split it further
          if self._estimate_token_count(paragraph) > self.max_tokens_per_window:
            # Split by sentences (crude approximation)
            sentences = paragraph.replace(". ", ".\n").split("\n")
            for sentence in sentences:
              if self._estimate_token_count(current_chunk + sentence) > self.max_tokens_per_window:
                if current_chunk:
                  chunks.append(current_chunk)
                  current_chunk = ""

                # If the sentence is still too large, split it by words
                if self._estimate_token_count(sentence) > self.max_tokens_per_window:
                  words = sentence.split(" ")
                  for word in words:
                    if self._estimate_token_count(current_chunk + word) > self.max_tokens_per_window:
                      chunks.append(current_chunk)
                      current_chunk = word + " "
                    else:
                      current_chunk += word + " "
                else:
                  current_chunk = sentence + " "
              else:
                current_chunk += sentence + " "
          else:
            current_chunk = paragraph
        else:
          if current_chunk:
            current_chunk += "\n\n" + paragraph
          else:
            current_chunk = paragraph

      # Add the last chunk if not empty
      if current_chunk:
        chunks.append(current_chunk)

      return chunks

    def process_large_content(self, content: str, processor: Callable[[str], str]) -> str:
      """
            Process large content by splitting into manageable chunks.
            
            Args:
                content: The content to process
                processor: Function to process each chunk
                
            Returns:
                Processed content reassembled from chunks
            """
      chunks = self.split_content(content)

      if len(chunks) == 1:
        return processor(content)

      # Process each chunk independently
      processed_chunks = [processor(chunk) for chunk in chunks]

      # Reassemble the processed chunks
      return "\n\n".join(processed_chunks)

  @dataclass
  class Patch:

    """Represents a patch containing content changes."""

    version: str
    """The version identifier for this patch"""

    description: str
    """A description of what this patch changes"""

    diff_content: str
    """The unified diff content"""

    changes: List[Dict[str, str]] = field(default_factory=list)
    """List of structured changes"""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    """When this patch was created"""

    def to_file(self, patch_dir: str) -> str:
      """
            Write the patch to a file and return the filename.
            
            Args:
                patch_dir: Directory to store patches
                
            Returns:
                Path to the created patch file
                
            Raises:
                IOError: If there's an error writing the file
            """
      # Ensure the patch directory exists
      Utilities.FileSystem.ensure_directory(patch_dir)

      # Create the filename from the version
      filename = os.path.join(patch_dir, f"patch-{self.version}.md")

      # Prepare the file content
      content = [f"# Patch {self.version}\n", f"Description: {self.description}", f"Timestamp: {self.timestamp}\n", "## Changes\n"]

      # Add the structured changes
      for change in self.changes:
        change_type = change.get("type", "UNKNOWN")
        location = change.get("location", "UNKNOWN")
        change_content = change.get("content", "")

        content.append(f"* {change_type}: {location}")
        if change_content:
          content.append("```")
          content.append(change_content)
          content.append("```\n")

      # Add the unified diff
      content.append("## Diff\n")
      content.append("```diff")
      content.append(self.diff_content)
      content.append("```")

      # Write to file
      Utilities.FileSystem.write_file(filename, "\n".join(content))
      return filename

    @classmethod
    def from_file(cls, filename: str) -> Self:
      """
            Create a Patch instance from a file.
            
            Args:
                filename: Path to the patch file
                
            Returns:
                A Patch instance
                
            Raises:
                ValueError: If the patch file is invalid or can't be parsed
                IOError: If there's an error reading the file
            """
      content = Utilities.FileSystem.read_file(filename)

      # Extract version from filename
      version_match = re.search(r"patch-(.+)\.md", os.path.basename(filename))
      if not version_match:
        raise ValueError(f"Invalid patch filename: {filename}")
      version = version_match.group(1)

      # Extract description and timestamp
      description_match = re.search(r"Description: (.+)$", content, re.MULTILINE)
      timestamp_match = re.search(r"Timestamp: (.+)$", content, re.MULTILINE)

      description = description_match.group(1) if description_match else ""
      timestamp = timestamp_match.group(1) if timestamp_match else ""

      # Extract the diff content
      diff_match = re.search(r"```diff\n([\s\S]+?)\n```", content)
      diff_content = diff_match.group(1) if diff_match else ""

      # Extract the changes
      changes = []
      changes_section = re.search(r"## Changes\n\n([\s\S]+?)(?=\n## Diff|\Z)", content)
      if changes_section:
        changes_text = changes_section.group(1)
        change_blocks = re.finditer(r"\* ([A-Z]+): ([^\n]+)(?:\n```\n([\s\S]+?)\n```)?", changes_text)

        for match in change_blocks:
          change_type = match.group(1)
          location = match.group(2)
          change_content = match.group(3) if match.group(3) else ""
          changes.append({"type": change_type, "location": location, "content": change_content})

      # Create and return the patch
      patch = cls(version, description, diff_content, changes)
      patch.timestamp = timestamp
      return patch

  class VersionManager:

    """Manages document versions and patches."""

    def __init__(self, base_file: str, patch_dir: str) -> None:
      """
            Initialize the version manager.
            
            Args:
                base_file: Path to the base document file
                patch_dir: Directory to store patches
                
            Raises:
                IOError: If there's an error reading the base file
            """
      self.base_file = base_file
      self.patch_dir = patch_dir
      self.base_content = ""
      self.patches: List[ContentManagement.Patch] = []

      # Ensure patch directory exists
      Utilities.FileSystem.ensure_directory(patch_dir)

      # Load base file if it exists
      if Utilities.FileSystem.file_exists(base_file):
        self.base_content = Utilities.FileSystem.read_file(base_file)

      # Load existing patches
      self.load_patches()

    def load_patches(self) -> None:
      """
            Load existing patches from the patch directory.
            
            Raises:
                ValueError: If a patch file is invalid or can't be parsed
            """
      self.patches = []

      # Get all patch files
      patch_files = Utilities.FileSystem.list_files(self.patch_dir, r"^patch-.*\.md$")

      if not patch_files:
        return

      # Sort patches by version
      def version_key(filename: str) -> Tuple[int, int, int]:
        """
                Generate a key for sorting patch versions.
                
                Args:
                    filename: Patch filename
                    
                Returns:
                    Tuple of (major, minor, patch) version numbers
                """
        version_match = re.search(r"patch-(.+)\.md", os.path.basename(filename))
        if not version_match:
          return (0, 0, 0)

        version = version_match.group(1)
        parts = version.split("-")

        # Pad with zeros for correct sorting
        if len(parts) == 1:
          return (int(parts[0]), 0, 0)
        elif len(parts) == 2:
          return (int(parts[0]), int(parts[1]), 0)
        else:
          return (int(parts[0]), int(parts[1]), int(parts[2]))

      patch_files.sort(key=version_key)

      # Load each patch
      for patch_file in patch_files:
        try:
          patch = ContentManagement.Patch.from_file(patch_file)
          self.patches.append(patch)
        except Exception as e:
          print(f"Error loading patch {patch_file}: {e}")

    def parse_version(self, version: str) -> ContentManagement.Version:
      """
            Parse a version string into its components.
            
            Args:
                version: Version string in format "major-minor-patch"
                
            Returns:
                Dictionary containing major, minor, and patch values
            """
      parts = version.split("-")
      result: ContentManagement.Version = {"major": 0, "minor": 0, "patch": 0}

      if len(parts) >= 1 and parts[0].isdigit():
        result["major"] = int(parts[0])
      if len(parts) >= 2 and parts[1].isdigit():
        result["minor"] = int(parts[1])
      if len(parts) >= 3 and parts[2].isdigit():
        result["patch"] = int(parts[2])

      return result

    def render(self) -> str:
      """
            Render the current state of the document by applying all patches.
            
            Returns:
                The document content with all patches applied
                
            Raises:
                ValueError: If a patch can't be applied cleanly
            """
      current_content = self.base_content

      # Apply each patch sequentially
      for patch in self.patches:
        # Apply the patch using Utilities.DiffManager
        try:
          current_content = Utilities.DiffManager.apply_diff(current_content, patch.diff_content)
        except ValueError as e:
          print(f"Warning: Failed to apply diff from patch {patch.version}: {e}")

          # Fall back to structured changes if diff application fails
          for change in patch.changes:
            change_type = change.get("type", "")
            location = change.get("location", "")
            content = change.get("content", "")

            if change_type == "ADD":
              # Simple append for fallback
              current_content += f"\n\n## {location}\n\n{content}"

            elif change_type == "REMOVE":
              # Basic pattern-based removal
              if location in current_content:
                pattern = rf"{re.escape(location)}.*?(?=\n## |\Z)"
                current_content = re.sub(pattern, "", current_content, flags=re.DOTALL)

            elif change_type == "REPLACE":
              # Basic pattern-based replacement
              if location in current_content:
                pattern = rf"{re.escape(location)}.*?(?=\n## |\Z)"
                current_content = re.sub(pattern, f"{location}\n\n{content}", current_content, flags=re.DOTALL)

      return current_content

    def add_patch(self, version: str, description: str, diff_content: str, changes: List[Dict[str, str]]) -> str:
      """
            Add a new patch and return the patch filename.
            
            Args:
                version: Version identifier
                description: Description of the changes
                diff_content: Unified diff content
                changes: List of structured changes
                
            Returns:
                Path to the created patch file
                
            Raises:
                IOError: If there's an error writing the patch file
            """
      patch = ContentManagement.Patch(version, description, diff_content, changes)
      patch_file = patch.to_file(self.patch_dir)
      self.patches.append(patch)
      return patch_file

    def save_iteration(self, iteration: int) -> str:
      """
            Save the current state as a complete iteration and return the filename.
            
            Args:
                iteration: Iteration number
                
            Returns:
                Path to the saved file
                
            Raises:
                ValueError: If a patch can't be applied cleanly
                IOError: If there's an error writing the file
            """
      content = self.render()
      output_file = f"article-{iteration}.md"
      Utilities.FileSystem.write_file(output_file, content)
      return output_file

  class ContentGenerator:

    """Generates content using LLM integration."""

    def __init__(
        self,
        llm_service: "Utilities.LLMService",
        template_manager: Optional["ContentManagement.TemplateManager"] = None,
        guidance_manager: Optional["ContentManagement.GuidanceManager"] = None,
        context_window_manager: Optional["ContentManagement.SimpleContextWindowManager"] = None) -> None:
      """
            Initialize the content generator.
            
            Args:
                llm_service: Service for language model interactions
                template_manager: Manager for prompt templates
                guidance_manager: Manager for guidance parameters
                context_window_manager: Manager for context window size constraints
            """
      self.llm_service = llm_service
      self.template_manager = template_manager or ContentManagement.TemplateManager()
      self.guidance_manager = guidance_manager or ContentManagement.GuidanceManager()
      self.context_window_manager = context_window_manager or ContentManagement.SimpleContextWindowManager()

    def generate_content(
        self,
        source_node: DocumentProcessing.Node,
        current_article: str,
        template_name: str = "default",
        guidance_name: str = "default",
        max_tokens: int = 2000,
        temperature: float = 0.7) -> Tuple[str, str, List[Dict[str, str]]]:
      """
            Generate content based on the source node and current article.
            
            Args:
                source_node: The source node containing content to integrate
                current_article: The current state of the article
                template_name: Name of the prompt template to use
                guidance_name: Name of the guidance parameters to use
                max_tokens: Maximum number of tokens to generate
                temperature: Controls randomness (0.0-1.0)
                
            Returns:
                - description: A description of the changes
                - enhanced_article: The complete article with new content integrated
                - changes: List of changes describing what was modified
                
            Raises:
                ContentManagement.ContentGenerationError: If content generation fails
                ContentManagement.TemplateError: If the template name doesn't exist
                ContentManagement.GuidanceError: If the guidance name doesn't exist
            """
      print(f"Processing node: {source_node.title} (level {source_node.level})")

      try:
        # Get template and guidance
        template = self.template_manager.get_template(template_name)
        guidance = self.guidance_manager.get_guidance(guidance_name)

        # Format prompts
        system_prompt = template.format_system_prompt(**guidance)
        user_prompt = template.format_user_prompt(section_title=source_node.title, source_content=source_node.content, current_article=current_article)

        # Generate content using the LLM service
        completion = self.llm_service.complete(system_prompt, user_prompt, max_tokens, temperature)

        # Parse the LLM response
        return self._parse_completion(completion, source_node, current_article)

      except Exception as e:
        if isinstance(e, (ContentManagement.TemplateError, ContentManagement.GuidanceError)):
          raise
        raise ContentManagement.ContentGenerationError(f"Content generation failed: {str(e)}") from e

    def _parse_completion(self, completion: str, source_node: DocumentProcessing.Node, current_article: str) -> Tuple[str, str, List[Dict[str, str]]]:
      """
            Parse the completion from the LLM.
            
            Args:
                completion: The LLM completion text
                source_node: The source node that was processed
                current_article: The current state of the article
                
            Returns:
                - description: A description of the changes
                - enhanced_article: The complete article with new content integrated
                - changes: List of changes describing what was modified
            """
      sections = completion.split("\n\n", 1)
      if len(sections) > 1:
        description = sections[0].strip()

        # Check if this is a SKIP operation
        if "SKIP" in description.upper():
          print(f"Skipping content from '{source_node.title}': {description}")
          return description, current_article, [{"type": "SKIP", "location": source_node.title, "content": ""}]

        content_sections = sections[1].split("Changes:", 1)

        if len(content_sections) > 1:
          enhanced_article = content_sections[0].strip()
          changes_text = content_sections[1].strip()

          # Parse the changes
          changes = []
          change_blocks = re.finditer(r"(ADD|REMOVE|REPLACE|SKIP):\s+([^\n]+)\s*(?:-\s*([^#]+))?", changes_text, re.MULTILINE)

          for match in change_blocks:
            operation = match.group(1).strip()
            location = match.group(2).strip()
            content = match.group(3).strip() if match.group(3) else ""

            changes.append({"type": operation, "location": location, "content": content})

            # If we find a SKIP operation, return immediately with no changes
            if operation == "SKIP":
              print(f"Skipping content from '{source_node.title}': {description}")
              return description, current_article, [{"type": "SKIP", "location": location, "content": ""}]
        else:
          # Couldn't parse changes section, use the entire content as the article
          enhanced_article = sections[1].strip()
          changes = [{"type": "ADD", "location": source_node.title, "content": f"Content from {source_node.title}"}]
      else:
        # Check if this is a simple SKIP response
        if "SKIP" in completion.upper():
          print(f"Skipping content from '{source_node.title}': {completion.strip()}")
          return completion.strip(), current_article, [{"type": "SKIP", "location": source_node.title, "content": ""}]

        # Fallback if we couldn't parse the response
        description = f"Update from {source_node.title}"
        enhanced_article = completion.strip()
        changes = [{"type": "ADD", "location": source_node.title, "content": f"Content from {source_node.title}"}]

      # If there are no changes detected but content is different, add a default change
      if not changes and enhanced_article != current_article:
        changes = [{"type": "ADD", "location": source_node.title, "content": f"Content from {source_node.title}"}]

      return description, enhanced_article, changes

# -----------------------------------------------------------------------------
# Utilities Layer
# -----------------------------------------------------------------------------

class Utilities:

  """Namespace for utility functions used across the application."""

  class LLMService(Protocol):

    """Protocol for language model service interactions."""

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
      """
            Generate a completion from the language model.
            
            Args:
                system_prompt: The system instructions to guide the model behavior
                user_prompt: The specific user query or content to process
                max_tokens: Maximum number of tokens to generate
                temperature: Controls randomness (0.0-1.0)
            
            Returns:
                The generated completion text
            """
      ...

  @dataclass
  class AzureOpenAIService:

    """Azure OpenAI API implementation of the LLM service."""

    endpoint: str
    """The API endpoint URL"""

    api_key: str
    """Authentication key for the API"""

    deployment_name: str
    """The model deployment identifier"""

    api_version: str = "2023-05-15"
    """API version to use"""

    max_retries: int = 3
    """Maximum number of retry attempts for failed requests"""

    retry_delay: float = 1.0
    """Base delay between retries in seconds"""

    def _send_request(self, url: str, data: dict, headers: dict, retry_count: int = 0) -> dict:
      """
            Send HTTP request with retry logic.
            
            Args:
                url: The request URL
                data: The request payload as a dictionary
                headers: HTTP headers
                retry_count: Current retry attempt
                
            Returns:
                Response data as a dictionary
                
            Raises:
                RuntimeError: If all retry attempts fail
            """
      try:
        # Convert data to JSON and encode
        json_data = json.dumps(data).encode('utf-8')

        # Create the request
        req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")

        # Send the request
        with urllib.request.urlopen(req) as response:
          return json.loads(response.read().decode('utf-8'))

      except urllib.error.HTTPError as e:
        # Get error details if available
        error_msg = f"HTTP error: {e.code} {e.reason}"
        try:
          error_details = json.loads(e.read().decode('utf-8'))
          error_msg += f"\nDetails: {error_details}"
        except:
          pass

        # Handle retry logic
        if retry_count < self.max_retries and (e.code >= 500 or e.code == 429):
          # Calculate backoff with exponential increase and jitter
          delay = self.retry_delay * (2**retry_count) * (0.5 + random.random())
          print(f"Request failed with {e.code}. Retrying in {delay:.2f} seconds...")
          time.sleep(delay)
          return self._send_request(url, data, headers, retry_count + 1)
        else:
          raise RuntimeError(error_msg) from e

      except Exception as e:
        raise RuntimeError(f"Request failed: {str(e)}") from e

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
      """
            Generate a completion using Azure OpenAI API.
            
            Args:
                system_prompt: The system instructions to guide the model behavior
                user_prompt: The specific user query or content to process
                max_tokens: Maximum number of tokens to generate
                temperature: Controls randomness (0.0-1.0)
                
            Returns:
                The generated completion text
                
            Raises:
                RuntimeError: If the API request fails after retries
            """
      # Prepare the request body
      request_body = {
        "messages": [{
          "role": "system",
          "content": system_prompt
        }, {
          "role": "user",
          "content": user_prompt
        }],
        "temperature": temperature,
        "max_tokens": max_tokens
      }

      # Prepare the request URL
      url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"

      # Prepare headers
      headers = {"Content-Type": "application/json", "api-key": self.api_key}

      # Send request with retry logic
      response_data = self._send_request(url, request_body, headers)

      # Extract and return the content
      return response_data["choices"][0]["message"]["content"]

  class FileSystem:

    """File system operations."""

    @staticmethod
    def ensure_directory(directory: str) -> None:
      """
            Ensure a directory exists, creating it if necessary.
            
            Args:
                directory: The directory path to ensure exists
                
            Raises:
                IOError: If the directory can't be created
            """
      os.makedirs(directory, exist_ok=True)

    @staticmethod
    def read_file(filepath: str, encoding: str = "utf-8") -> str:
      """
            Read content from a file.
            
            Args:
                filepath: Path to the file to read
                encoding: Text encoding to use (default: utf-8)
                
            Returns:
                The file content as a string
                
            Raises:
                FileNotFoundError: If the file doesn't exist
                IOError: If there's an error reading the file
            """
      with open(filepath, "r", encoding=encoding) as f:
        return f.read()

    @staticmethod
    def write_file(filepath: str, content: str, encoding: str = "utf-8") -> None:
      """
            Write content to a file.
            
            Args:
                filepath: Path to the file to write
                content: Content to write to the file
                encoding: Text encoding to use (default: utf-8)
                
            Raises:
                IOError: If there's an error writing to the file
            """
      # Ensure the directory exists
      os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

      with open(filepath, "w", encoding=encoding) as f:
        f.write(content)

    @staticmethod
    def list_files(directory: str, pattern: Optional[str] = None) -> List[str]:
      """
            List files in a directory, optionally filtered by a pattern.
            
            Args:
                directory: The directory path to list files from
                pattern: Optional regex pattern to filter files
                
            Returns:
                List of file paths matching the pattern
                
            Raises:
                FileNotFoundError: If the directory doesn't exist
            """
      if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")

      files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

      if pattern:
        regex = re.compile(pattern)
        files = [f for f in files if regex.search(os.path.basename(f))]

      return files

    @staticmethod
    def file_exists(filepath: str) -> bool:
      """
            Check if a file exists.
            
            Args:
                filepath: Path to the file to check
                
            Returns:
                True if the file exists, False otherwise
            """
      return os.path.isfile(filepath)

  class DiffManager:

    """Manages creation and application of diffs between text content."""

    @staticmethod
    def create_diff(original: str, modified: str) -> str:
      """
            Create a unified diff between two text strings.
            
            Args:
                original: The original text content
                modified: The modified text content
                
            Returns:
                A unified diff as a string
            """
      diff_lines = list(difflib.unified_diff(original.splitlines(), modified.splitlines(), fromfile="original", tofile="modified", lineterm=""))
      return "\n".join(diff_lines)

    @staticmethod
    def apply_diff(content: str, diff_content: str) -> str:
      """
            Apply a unified diff to a text string.
            
            Args:
                content: The original content to modify
                diff_content: The unified diff to apply
                
            Returns:
                The modified content with diff applied
                
            Raises:
                ValueError: If the diff cannot be applied cleanly
            """
      # Split content into lines
      lines = content.splitlines()
      result_lines = lines.copy()

      # Parse diff content into lines
      diff_lines = diff_content.splitlines()

      if not diff_lines:
        return content # No changes

      # Track line offset to handle multiple diff hunks
      line_offset = 0
      current_line = None

      # Process each line in the diff
      i = 0
      while i < len(diff_lines):
        line = diff_lines[i]

        # Handle diff headers to get line numbers
        if line.startswith("@@"):
          # Parse the @@ -a,b +c,d @@ format
          header_match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
          if not header_match:
            raise ValueError(f"Invalid diff header format: {line}")

          # Extract line numbers (1-based in diff, convert to 0-based)
          src_line = int(header_match.group(1)) - 1
          tgt_line = int(header_match.group(2)) - 1

          # Adjust for previous changes
          current_line = tgt_line + line_offset

        # Process content lines
        elif line.startswith("-"):
          # Line should be removed
          if current_line is None:
            raise ValueError("Malformed diff: content line before header")

          if 0 <= current_line < len(result_lines):
            result_lines.pop(current_line)
            line_offset -= 1
          else:
            raise ValueError(f"Diff error: trying to remove line {current_line} but content only has {len(result_lines)} lines")

        elif line.startswith("+"):
          # Line should be added
          if current_line is None:
            raise ValueError("Malformed diff: content line before header")

          content_to_add = line[1:] # Remove the + prefix
          if 0 <= current_line <= len(result_lines):
            result_lines.insert(current_line, content_to_add)
            current_line += 1
            line_offset += 1
          else:
            raise ValueError(f"Diff error: trying to add at line {current_line} but content only has {len(result_lines)} lines")

        elif not line.startswith("---") and not line.startswith("+++"):
          # Context line - just advance the position
          if current_line is not None:
            current_line += 1

        i += 1

      # Reassemble the content
      return "\n".join(result_lines)

# -----------------------------------------------------------------------------
# Application Layer
# -----------------------------------------------------------------------------

class Application:

  """Namespace for application-level functionality."""

  class ConfigurationError(Exception):

    """Exception raised for errors in the application configuration."""
    pass

  class Configuration:

    """Manages application configuration."""

    @staticmethod
    def from_args(args: argparse.Namespace) -> Dict[str, Any]:
      """
            Create configuration from command-line arguments.
            
            Args:
                args: Parsed command-line arguments
                
            Returns:
                Dictionary containing configuration values
                
            Raises:
                Application.ConfigurationError: If the configuration is invalid
            """
      try:
        # Determine source type based on files argument
        is_stdin = False
        file_list = []

        if not args.files or (len(args.files) == 1 and args.files[0] == '-'):
          # No files or dash indicates stdin
          is_stdin = True
        else:
          # Use files from arguments
          file_list = args.files

        config = {
          "action": args.action,
          "source": {
            "type": "stdin" if is_stdin else "files",
            "value": None if is_stdin else file_list,
            "concat_stream": args.concat_stream if is_stdin else False
          },
          "output": {
            "format": args.output_format,
            "file": args.output_file,
          },
          "processing": {
            "max_header_level": args.max_header_level,
          }
        }

        # Handle guidance parameters
        if args.guidance_file:
          config["guidance"] = {"file": args.guidance_file, "name": args.guidance_name or "default"}
        elif args.guidance_inline:
          # Parse inline guidance parameters
          guidance_params = Application.Configuration._parse_inline_guidance(args.guidance_inline)
          config["guidance"] = {"inline": guidance_params, "name": "inline"}
        else:
          config["guidance"] = {"name": args.guidance_name or "default"}

        # Handle template parameters
        if args.template_file:
          config["template"] = {"file": args.template_file, "name": args.template_name or "default"}
        else:
          config["template"] = {"name": args.template_name or "default"}

        # Process LLM configuration if provided
        llm_config = Application.Configuration._get_llm_config(args)
        if llm_config:
          config["llm"] = llm_config

        # Process patch/render configuration if provided
        if args.action == "render":
          config["render"] = {"base_file": args.base_file or "base.md", "patch_dir": args.patch_dir or "patches"}

        return config

      except Exception as e:
        if not isinstance(e, Application.ConfigurationError):
          raise Application.ConfigurationError(f"Failed to create configuration: {str(e)}")
        raise

    @staticmethod
    def _parse_inline_guidance(guidance_str: str) -> Dict[str, str]:
      """
            Parse inline guidance parameters from a string.
            
            Format: key1=value1,key2=value2,...
            
            Args:
                guidance_str: Comma-separated key-value pairs
                
            Returns:
                Dictionary of guidance parameters
                
            Raises:
                Application.ConfigurationError: If the format is invalid
            """
      guidance_params = {}

      try:
        pairs = guidance_str.split(",")
        for pair in pairs:
          key, value = pair.split("=", 1)
          guidance_params[key.strip()] = value.strip()
      except ValueError:
        raise Application.ConfigurationError(f"Invalid guidance parameter format: {guidance_str}")

      # Validate required parameters
      required_params = ["style", "audience", "structure", "formatting", "constraints"]
      missing_params = [param for param in required_params if param not in guidance_params]

      if missing_params:
        raise Application.ConfigurationError(f"Missing guidance parameters: {', '.join(missing_params)}")

      return guidance_params

    @staticmethod
    def _get_llm_config(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
      """
            Extract LLM configuration from arguments or environment.
            
            Args:
                args: Parsed command-line arguments
                
            Returns:
                Dictionary with LLM configuration or None if not available
            """
      # Try to get values from args first, then environment variables
      endpoint = getattr(args, 'azure_endpoint', None) or os.environ.get("AZURE_OPENAI_ENDPOINT")
      api_key = getattr(args, 'azure_key', None) or os.environ.get("AZURE_OPENAI_KEY")
      deployment = getattr(args, 'azure_deployment', None) or os.environ.get("AZURE_OPENAI_DEPLOYMENT")

      # Create config if all required values are available
      if endpoint and api_key and deployment:
        return {
          "type": "azure",
          "endpoint": endpoint,
          "api_key": api_key,
          "deployment": deployment,
          "max_retries": getattr(args, 'max_retries', 3),
          "retry_delay": getattr(args, 'retry_delay', 1.0),
          "temperature": getattr(args, 'temperature', 0.7),
        }
      elif getattr(args, 'mock_llm', False):
        return {
          "type": "mock",
          "temperature": getattr(args, 'temperature', 0.7),
        }

      return None

    @staticmethod
    def from_env() -> Dict[str, Any]:
      """
            Load configuration from environment variables.
            
            Returns:
                Dictionary containing configuration values from environment
            """
      config = {
        "source": {
          "type": os.environ.get("KB_SOURCE_TYPE", "file"),
          "value": os.environ.get("KB_SOURCE", "input.md"),
        },
        "output": {
          "format": os.environ.get("KB_OUTPUT_FORMAT", "markdown"),
          "file": os.environ.get("KB_OUTPUT_FILE", "output.md"),
        },
        "processing": {
          "mode": os.environ.get("KB_PROCESSING_MODE", "auto"),
          "max_header_level": int(os.environ.get("KB_MAX_HEADER_LEVEL", "6")),
        },
        "guidance": {
          "name": os.environ.get("KB_GUIDANCE_NAME", "default"),
          "file": os.environ.get("KB_GUIDANCE_FILE", ""),
        },
        "template": {
          "name": os.environ.get("KB_TEMPLATE_NAME", "default"),
          "file": os.environ.get("KB_TEMPLATE_FILE", ""),
        }
      }

      return config

  class KnowledgeBaseGenerator:

    """Main class for generating knowledge base articles."""

    def __init__(
        self,
        config: Dict[str, Any],
        content_generator: Optional[ContentManagement.ContentGenerator] = None,
        template_manager: Optional[ContentManagement.TemplateManager] = None,
        guidance_manager: Optional[ContentManagement.GuidanceManager] = None) -> None:
      """
            Initialize the knowledge base generator.
            
            Args:
                config: Application configuration
                content_generator: Optional content generator
                template_manager: Optional template manager
                guidance_manager: Optional guidance manager
                
            Raises:
                Application.ConfigurationError: If the configuration is invalid
            """
      self.config = config
      self.template_manager = template_manager or ContentManagement.TemplateManager()
      self.guidance_manager = guidance_manager or ContentManagement.GuidanceManager()

      # Initialize components based on configuration
      self._initialize_components()

      # Content generator will be initialized when needed
      self.content_generator = content_generator

    def _initialize_components(self) -> None:
      """
            Initialize components based on configuration.
            
            Raises:
                Application.ConfigurationError: If component initialization fails
            """
      try:
        # Load templates if specified
        if "template" in self.config and "file" in self.config["template"]:
          template_file = self.config["template"]["file"]
          if template_file:
            try:
              loaded_templates = self.template_manager.load_template_file(template_file)
              print(f"Loaded templates: {', '.join(loaded_templates)}")
            except ContentManagement.TemplateError as e:
              print(f"Warning: Failed to load templates: {str(e)}")

        # Load guidance if specified
        if "guidance" in self.config:
          if "file" in self.config["guidance"] and self.config["guidance"]["file"]:
            try:
              loaded_guidance = self.guidance_manager.load_guidance_file(self.config["guidance"]["file"])
              print(f"Loaded guidance profiles: {', '.join(loaded_guidance)}")
            except ContentManagement.GuidanceError as e:
              print(f"Warning: Failed to load guidance: {str(e)}")
          elif "inline" in self.config["guidance"]:
            # Add inline guidance
            self.guidance_manager.add_guidance("inline", self.config["guidance"]["inline"])
      except Exception as e:
        raise Application.ConfigurationError(f"Failed to initialize components: {str(e)}")

    def _create_markdown_stream(self) -> DocumentProcessing.MarkdownStream:
      """
            Create a markdown stream based on configuration.
            
            Returns:
                Configured markdown stream
                
            Raises:
                Application.ConfigurationError: If the source configuration is invalid
            """
      source_type = self.config["source"]["type"]
      source_value = self.config["source"]["value"]

      try:
        if source_type == "file":
          return DocumentProcessing.FileMarkdownStream(source_value)

        elif source_type == "string":
          return DocumentProcessing.StringMarkdownStream(source_value)

        elif source_type == "stdin":
          return DocumentProcessing.StdinMarkdownStream()

        elif source_type == "files":
          # Create a concatenated stream from multiple files
          files = source_value.split(",")
          content = ""
          for file in files:
            with open(file.strip(), "r", encoding="utf-8") as f:
              content += f.read() + "\n\n"
          return DocumentProcessing.StringMarkdownStream(content)

        else:
          raise Application.ConfigurationError(f"Unknown source type: {source_type}")

      except Exception as e:
        if not isinstance(e, Application.ConfigurationError):
          raise Application.ConfigurationError(f"Failed to create markdown stream: {str(e)}")
        raise

    def _get_content_selector(self) -> ContentManagement.ContentSelector:
      """
            Create a content selector based on configuration.
            
            Returns:
                Configured content selector
            """
      selector = ContentManagement.ContentSelector()

      # Add header level rule if specified
      max_header_level = self.config["processing"].get("max_header_level")
      if max_header_level is not None and 1 <= max_header_level <= 6:
        selector.add_rule(ContentManagement.create_header_level_rule(max_header_level))

      # Add other rules based on configuration
      # (This would be expanded based on available configuration options)

      return selector

    def _initialize_content_generator(self, llm_service: Utilities.LLMService) -> None:
      """
            Initialize the content generator.
            
            Args:
                llm_service: LLM service for content generation
            """
      if self.content_generator is None:
        self.content_generator = ContentManagement.ContentGenerator(llm_service, self.template_manager, self.guidance_manager)

    def _get_llm_service(self) -> Utilities.LLMService:
      """
            Create an LLM service based on configuration.
            
            Returns:
                Configured LLM service
                
            Raises:
                Application.ConfigurationError: If the LLM configuration is invalid
            """
      try:
        if "llm" not in self.config:
          return Utilities.MockLLMService()

        llm_config = self.config["llm"]
        llm_type = llm_config.get("type", "mock")

        if llm_type == "azure":
          return Utilities.AzureOpenAIService(
            endpoint=llm_config["endpoint"],
            api_key=llm_config["api_key"],
            deployment_name=llm_config["deployment"],
            api_version="2023-05-15",
            max_retries=llm_config.get("max_retries", 3),
            retry_delay=llm_config.get("retry_delay", 1.0))
        else:
          # Default to mock service
          return Utilities.MockLLMService()

      except Exception as e:
        raise Application.ConfigurationError(f"Failed to create LLM service: {str(e)}")

    def generate(self) -> str:
      """
            Generate a knowledge base article based on configuration.
            
            Returns:
                The generated article content
                
            Raises:
                Application.ConfigurationError: If generation fails due to configuration issues
            """
      try:
        # Create markdown stream
        stream = self._create_markdown_stream()

        # Parse the markdown
        processing_mode = self.config["processing"]["mode"]

        if processing_mode == "incremental":
          # Use incremental processing
          builder = DocumentProcessing.IncrementalTreeBuilder(stream)
          tree = builder.build_complete_tree()
        else:
          # Use default processing
          tree = DocumentProcessing.StreamMarkdownParser.parse_stream(stream)

        # Filter nodes based on content selector
        selector = self._get_content_selector()
        nodes = [node for node, _ in tree.dfs_traversal() if node != tree.root]
        selected_nodes = selector.filter_nodes(nodes)

        print(f"Selected {len(selected_nodes)}/{len(nodes)} nodes for processing")

        # Get LLM service and initialize content generator
        llm_service = self._get_llm_service()
        self._initialize_content_generator(llm_service)

        # Generate content
        current_article = ""
        template_name = self.config["template"]["name"]
        guidance_name = self.config["guidance"]["name"]

        # This could be improved with patch-based versioning
        # if that level of robustness is required
        for node in selected_nodes:
          description, current_article, changes = self.content_generator.generate_content(node, current_article, template_name, guidance_name)

          # Log the changes
          print(f"- {description}")
          for change in changes:
            change_type = change.get("type", "UNKNOWN")
            location = change.get("location", "UNKNOWN")
            print(f"  {change_type}: {location}")

        # Format the output based on configuration
        output_format = self.config["output"]["format"]
        if output_format == "markdown":
          formatted_output = current_article
        elif output_format == "html":
          # Convert markdown to HTML (placeholder)
          formatted_output = f"<html><body>{current_article}</body></html>"
        else:
          formatted_output = current_article

        # Save to file if specified
        output_file = self.config["output"].get("file")
        if output_file:
          Utilities.FileSystem.write_file(output_file, formatted_output)
          print(f"Output saved to: {output_file}")

        return formatted_output

      except Exception as e:
        if not isinstance(e, Application.ConfigurationError):
          raise Application.ConfigurationError(f"Generation failed: {str(e)}")
        raise

    def validate(self) -> List[str]:
      """
            Validate the source document.
            
            Returns:
                List of validation warnings/errors
                
            Raises:
                Application.ConfigurationError: If validation fails due to configuration issues
            """
      try:
        # Create markdown stream
        stream = self._create_markdown_stream()

        # Parse the markdown
        tree = DocumentProcessing.StreamMarkdownParser.parse_stream(stream)

        # Get validation warnings
        warnings = tree.validate()

        # Print warnings
        if warnings:
          print("Validation warnings:")
          for warning in warnings:
            print(f"- {warning}")
        else:
          print("Document is valid.")

        return warnings

      except Exception as e:
        if not isinstance(e, Application.ConfigurationError):
          raise Application.ConfigurationError(f"Validation failed: {str(e)}")
        raise

  @staticmethod
  def concat_files(file_paths: List[str], output_file=None) -> None:
    """
        Concatenate multiple markdown files with document separators using
        incremental file processing to minimize memory usage.
        
        Args:
            file_paths: List of files to concatenate
            output_file: Optional file handle to write to (defaults to sys.stdout)
            
        Raises:
            FileNotFoundError: If any file doesn't exist
            IOError: If there's an error reading any file
        """
    if not file_paths:
      raise ValueError("No files specified for concatenation")

    # Use stdout as default output
    output = output_file or sys.stdout

    # Process one file at a time
    for file_path in file_paths:
      try:
        # Get file size from stat before opening
        file_stats = os.stat(file_path)
        file_size = file_stats.st_size

        # Create document separator
        separator = f'<!-- DOC name="{os.path.basename(file_path)}" size_of={file_size} -->'
        output.write(separator)

        # Process file in chunks to avoid loading it all into memory
        with open(file_path, 'r', encoding='utf-8') as f:
          while True:
            chunk = f.read(65536) # 64KB chunks
            if not chunk:
              break
            output.write(chunk)

      except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
      except IOError as e:
        raise IOError(f"Error reading {file_path}: {str(e)}") #!/usr/bin/env python3

  @staticmethod
  def create_cli_parser() -> argparse.ArgumentParser:
    """
        Create the command-line interface parser.
        
        Returns:
            Configured argument parser
        """
    parser = argparse.ArgumentParser(
      description="Generate knowledge base articles by processing markdown sources.",
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog="""
Examples:
  # Generate a knowledge base article from multiple files
  python kb_generator.py generate file1.md file2.md --output-file output.md

  # Generate from standard input
  cat input.md | python kb_generator.py generate

  # Generate from standard input (explicit)
  cat input.md | python kb_generator.py generate -

  # Process a concatenated stream with document separators
  cat combined.md | python kb_generator.py generate - --concat-stream

  # Concatenate multiple files and output to stdout
  python kb_generator.py concat file1.md file2.md > combined.md

  # Use custom guidance
  python kb_generator.py generate file1.md --guidance-file guidance.json --guidance-name technical

Environment Variables:
  - AZURE_OPENAI_ENDPOINT: URL for Azure OpenAI endpoint
  - AZURE_OPENAI_KEY: API key for Azure OpenAI
  - AZURE_OPENAI_DEPLOYMENT: Deployment name in Azure
  - KB_OUTPUT_FORMAT: Output format (markdown, html)
  - KB_OUTPUT_FILE: Output file path
  - KB_MAX_HEADER_LEVEL: Maximum header level to process (1-6)
  - KB_GUIDANCE_NAME: Guidance profile name
  - KB_GUIDANCE_FILE: Path to guidance JSON file
  - KB_TEMPLATE_NAME: Template name
  - KB_TEMPLATE_FILE: Path to template JSON file
""")

    # Add action argument
    parser.add_argument(
      "action",
      choices=["generate", "validate", "render", "concat"],
      help="Action to perform: generate an article, validate source, render patches, or concat files")

    # Add file arguments - for both concat and generate/validate actions
    parser.add_argument("files", nargs="*", help="List of markdown files to process. Use '-' or no files to read from stdin.")

    # Stdin options
    parser.add_argument("--concat-stream", action="store_true", help="Whether stdin input is already a concatenated stream with document separators")

    # Output options
    parser.add_argument("--output-format", choices=["markdown", "html"], default="markdown", help="Output format (default: markdown)")
    parser.add_argument("--output-file", "-o", help="Output file path (stdout if not specified)")

    # Processing options
    parser.add_argument("--max-header-level", type=int, choices=range(1, 7), default=6, help="Maximum header level to process (1-6, default: 6)")

    # Guidance options
    parser.add_argument("--guidance-file", help="Path to JSON file containing guidance profiles")
    parser.add_argument("--guidance-name", help="Name of guidance profile to use (default: default)")
    parser.add_argument("--guidance-inline", help="Inline guidance parameters (format: style=value,audience=value,...)")

    # Template options
    parser.add_argument("--template-file", help="Path to JSON file containing prompt templates")
    parser.add_argument("--template-name", help="Name of template to use (default: default)")

    # LLM options
    parser.add_argument("--azure-endpoint", help="Azure OpenAI API endpoint URL (or set AZURE_OPENAI_ENDPOINT env variable)")
    parser.add_argument("--azure-key", help="Azure OpenAI API key (or set AZURE_OPENAI_KEY env variable)")
    parser.add_argument("--azure-deployment", help="Azure OpenAI deployment name (or set AZURE_OPENAI_DEPLOYMENT env variable)")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature for generation (0.0 to 1.0, default: 0.7)")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum number of retry attempts for API calls (default: 3)")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="Base delay between retries in seconds (default: 1.0)")
    parser.add_argument("--mock-llm", action="store_true", help="Use mock LLM service instead of Azure OpenAI")

    # Version control options (for render action)
    parser.add_argument("--base-file", help="Base file for patch application (for render action)")
    parser.add_argument("--patch-dir", help="Directory containing patches (for render action)")

    return parser

  @staticmethod
  def main() -> None:
    """
        Main entry point for the application.
        
        This function:
        1. Parses command-line arguments
        2. Creates the appropriate components
        3. Performs the requested action
        """
    # Parse command-line arguments
    parser = Application.create_cli_parser()
    args = parser.parse_args()

    try:
      if args.action == "concat":
        # Handle concat separately with streaming implementation
        if not args.files:
          raise ValueError("No files specified for concatenation")

        # Process files incrementally and write directly to stdout
        Application.concat_files(args.files)
        return

      # For all other actions, extract full configuration
      config = Application.Configuration.from_args(args)

      # Create knowledge base generator
      generator = Application.KnowledgeBaseGenerator(config)

      # Perform the requested action
      if config["action"] == "generate":
        output = generator.generate()

        # Print to stdout if no output file specified
        if not config["output"].get("file"):
          print(output)

      elif config["action"] == "validate":
        generator.validate()

      elif config["action"] == "render":
        # Render from patches
        output = generator.render()

        # Print to stdout if no output file specified
        if not config["output"].get("file"):
          print(output)

    except (ValueError, FileNotFoundError, IOError) as e:
      print(f"Error: {str(e)}", file=sys.stderr)
      sys.exit(1)
    except Application.ConfigurationError as e:
      print(f"Configuration error: {str(e)}", file=sys.stderr)
      sys.exit(1)
    except Exception as e:
      print(f"Error: {str(e)}", file=sys.stderr)
      import traceback
      traceback.print_exc(file=sys.stderr)
      sys.exit(1)

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
  Application.main()
