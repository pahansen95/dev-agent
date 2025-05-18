#!/usr/bin/env python3
"""
# Alloy QuickStart Guide Generator

A tool for procedurally generating Alloy Specification Language documentation by
processing source material and applying intelligent content transformations.

## Overview

This application automatically transforms comprehensive Alloy reference material into
concise quickstart guides through an iterative, LLM-assisted process. It analyzes source
content, determines optimal integration points, and creates structured patches that
progressively build a complete guide.

Key capabilities:
- Markdown document parsing and hierarchical representation
- Intelligent content selection and integration
- Structured version control with diff-based patches
- LLM-powered content generation and refinement
- Deterministic and reproducible guide creation

## Architectural Design

The application follows a layered architecture with clear boundaries:

1. **Document Processing Layer**
   - Parses source markdown into navigable tree structures
   - Manages document hierarchies and content extraction
   - Provides traversal mechanisms for sequential processing

2. **Content Management Layer**
   - Handles content generation through LLM integration
   - Implements versioning with structured patch management
   - Controls content transformations and diff generation

3. **Utilities Layer**
   - Provides cross-cutting functionality like LLM services
   - Handles file operations and diff management
   - Implements retry logic and error handling

4. **Application Layer**
   - Orchestrates document processing and content management
   - Manages configuration and command-line interface
   - Controls the overall workflow and user interaction

Data flows through these layers in a single direction: the application layer coordinates
document processing to extract content, then uses content management to generate guide
sections, finally utilizing utilities to persist results.

## Contributor Guidelines

### Coding Style

- **Python Version**: Requires Python 3.10+ for compatibility with typing features
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
- **Code Formatting**: Follow PEP 8 guidelines for spacing and formatting

### Additional Directives

- **Error Handling**: Propagate exceptions to appropriate layers; avoid silent failures
- **Dependency Injection**: Use explicit dependency injection for testability
- **Interface Contracts**: Define clear protocols for cross-layer interactions
- **Performance**: Minimize redundant file operations and LLM calls
- **Maintainability**: Prioritize readability and clear intent over cleverness

When adding new functionality:
1. Identify the appropriate layer
2. Implement as a class or method within existing namespaces
3. Update interfaces as needed, maintaining backward compatibility
4. Add comprehensive docstrings and type annotations
5. Consider error cases and edge conditions

This architecture ensures separation of concerns while maintaining a cohesive application
that can evolve through contribution.
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
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Protocol, Self, Tuple, TypedDict, Union, cast


# -----------------------------------------------------------------------------
# Document Processing Layer
# -----------------------------------------------------------------------------

class DocumentProcessing:
    """Namespace for document processing functionality."""
    
    class ParsingError(Exception):
        """Exception raised for errors during markdown parsing."""
        pass
    
    class Node:
        """Represents a node in the markdown document tree."""
        
        def __init__(
            self, 
            level: int, 
            title: str, 
            content: str = "", 
            parent: Optional["DocumentProcessing.Node"] = None
        ) -> None:
            self.level: int = level  # Header level (1 for #, 2 for ##, etc.)
            self.title: str = title.strip()
            self.content: str = content
            self.parent: Optional["DocumentProcessing.Node"] = parent
            self.children: List["DocumentProcessing.Node"] = []
        
        def add_child(self, child: "DocumentProcessing.Node") -> None:
            """Add a child node to this node."""
            child.parent = self
            self.children.append(child)
        
        def is_empty(self) -> bool:
            """Check if the node has no meaningful content."""
            return not self.content.strip() and not self.children
        
        def __repr__(self) -> str:
            return f"Node(level={self.level}, title='{self.title}', children={len(self.children)})"
    
    class Tree:
        """Represents a tree structure of a markdown document."""
        
        def __init__(self) -> None:
            self.root: DocumentProcessing.Node = DocumentProcessing.Node(0, "ROOT")
            self.current: DocumentProcessing.Node = self.root
        
        def add_node(self, level: int, title: str, content: str = "") -> DocumentProcessing.Node:
            """Add a node to the tree at the appropriate level."""
            # Find the appropriate parent for this node
            parent: DocumentProcessing.Node = self.root
            node: DocumentProcessing.Node = self.root
            
            # Traverse up the tree until we find a node with a lower level
            while node.level >= level and node.parent is not None:
                node = node.parent
            
            parent = node
            
            # Create and add the new node
            new_node = DocumentProcessing.Node(level, title, content, parent)
            parent.add_child(new_node)
            self.current = new_node
            
            return new_node
        
        def dfs_traversal(self) -> List[Tuple[DocumentProcessing.Node, int]]:
            """Perform a depth-first traversal of the tree, returning node and depth pairs."""
            result: List[Tuple[DocumentProcessing.Node, int]] = []
            
            def _dfs(node: DocumentProcessing.Node, depth: int = 0) -> None:
                result.append((node, depth))
                for child in node.children:
                    _dfs(child, depth + 1)
            
            _dfs(self.root)
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
                # Skip root node
                if node == self.root:
                    continue
                
                # Check for empty nodes
                if node.is_empty():
                    warnings.append(f"Empty node found: '{node.title}'")
                
                # Check for invalid level jumps (e.g., h1 -> h3)
                if node.parent and node.parent != self.root:
                    if node.level > node.parent.level + 1:
                        warnings.append(
                            f"Header level jump from {node.parent.level} to {node.level} "
                            f"at node '{node.title}'"
                        )
            
            return warnings
    
    class Parser:
        """Parses a markdown file into a tree structure."""
        
        @staticmethod
        def parse_file(filename: str) -> DocumentProcessing.Tree:
            """
            Parse a markdown file into a tree structure.
            
            Args:
                filename: Path to the markdown file
                
            Returns:
                A tree representation of the markdown structure
                
            Raises:
                DocumentProcessing.ParsingError: If there's an error parsing the file
            """
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read()
                return DocumentProcessing.Parser.parse_string(content)
            except FileNotFoundError:
                raise DocumentProcessing.ParsingError(f"File not found: {filename}")
            except UnicodeDecodeError:
                raise DocumentProcessing.ParsingError(f"Encoding error in file: {filename}")
            except Exception as e:
                raise DocumentProcessing.ParsingError(f"Error reading file {filename}: {str(e)}") from e
        
        @staticmethod
        def parse_string(content: str) -> DocumentProcessing.Tree:
            """
            Parse a markdown string into a tree structure.
            
            Args:
                content: Markdown content as a string
                
            Returns:
                A tree representation of the markdown structure
                
            Raises:
                DocumentProcessing.ParsingError: If there's an error in the markdown structure
            """
            tree = DocumentProcessing.Tree()
            current_node = tree.root
            current_content: List[str] = []
            
            lines = content.splitlines()
            
            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                header_match = re.match(r"^(#+)\s+(.+)$", line)
                
                if header_match:
                    # If we have accumulated content, add it to the current node
                    if current_content:
                        current_node.content += "\n".join(current_content)
                        current_content = []
                    
                    # Create a new node for this header
                    level = len(header_match.group(1))
                    title = header_match.group(2)
                    
                    # Check for empty title
                    if not title.strip():
                        raise DocumentProcessing.ParsingError(f"Empty header title at line {i+1}")
                    
                    # Check for excessively deep header level
                    if level > 6:
                        raise DocumentProcessing.ParsingError(
                            f"Header level too deep (level {level}) at line {i+1}: {line}"
                        )
                    
                    current_node = tree.add_node(level, title)
                else:
                    # Add this line to the accumulated content
                    current_content.append(line)
                
                i += 1
            
            # Add any remaining content to the last node
            if current_content and current_node != tree.root:
                current_node.content += "\n".join(current_content)
            
            # Validate the tree
            warnings = tree.validate()
            if warnings:
                # Just log warnings but don't fail
                print("Markdown parsing warnings:")
                for warning in warnings:
                    print(f"- {warning}")
            
            return tree


# -----------------------------------------------------------------------------
# Content Management Layer
# -----------------------------------------------------------------------------

class ContentManagement:
    """Namespace for content management functionality."""
    
    class ChangeType(Enum):
        """Types of content changes."""
        ADD = "ADD"
        REMOVE = "REMOVE"
        REPLACE = "REPLACE"
        SKIP = "SKIP"  # No modification needed
    
    class Change(TypedDict):
        """Represents a single content change."""
        type: str  # "ADD", "REMOVE", or "REPLACE"
        location: str  # Section title or identifier
        content: str  # The content being added, removed, or used as replacement
    
    class Version(TypedDict):
        """Type for version information."""
        major: int
        minor: int
        patch: int
    
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
            """Write the patch to a file and return the filename."""
            # Ensure the patch directory exists
            Utilities.FileSystem.ensure_directory(patch_dir)
            
            # Create the filename from the version
            filename = os.path.join(patch_dir, f"patch-{self.version}.md")
            
            # Prepare the file content
            content = [
                f"# Patch {self.version}\n",
                f"Description: {self.description}",
                f"Timestamp: {self.timestamp}\n",
                "## Changes\n"
            ]
            
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
            """Create a Patch instance from a file."""
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
                    changes.append({
                        "type": change_type, 
                        "location": location, 
                        "content": change_content
                    })
            
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
            """Load existing patches from the patch directory."""
            self.patches = []
            
            # Get all patch files
            patch_files = Utilities.FileSystem.list_files(self.patch_dir, r"^patch-.*\.md$")
            
            if not patch_files:
                return
            
            # Sort patches by version
            def version_key(filename: str) -> Tuple[int, int, int]:
                version = re.search(r"patch-(.+)\.md", os.path.basename(filename)).group(1)
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
            """Parse a version string into its components."""
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
            """Render the current state of the document by applying all patches."""
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
                                current_content = re.sub(
                                    pattern, f"{location}\n\n{content}", current_content, flags=re.DOTALL
                                )
            
            return current_content
        
        def add_patch(
            self, 
            version: str, 
            description: str, 
            diff_content: str, 
            changes: List[Dict[str, str]]
        ) -> str:
            """Add a new patch and return the patch filename."""
            patch = ContentManagement.Patch(version, description, diff_content, changes)
            patch_file = patch.to_file(self.patch_dir)
            self.patches.append(patch)
            return patch_file
        
        def save_iteration(self, iteration: int) -> str:
            """Save the current state as a complete iteration and return the filename."""
            content = self.render()
            output_file = f"guide-{iteration}.md"
            Utilities.FileSystem.write_file(output_file, content)
            return output_file
    
    class ContentGenerator:
        """Generates content using an LLM service."""
        
        @staticmethod
        def generate_content(
            source_node: DocumentProcessing.Node,
            current_guide: str,
            author_guidance: str,
            llm_service: Utilities.LLMService
        ) -> Tuple[str, str, List[Dict[str, str]]]:
            """
            Generate content based on the source node and current guide.
            
            Args:
                source_node: The source node containing content to integrate
                current_guide: The current state of the guide
                author_guidance: Guidance for authoring
                llm_service: Service for language model interactions
                
            Returns:
                - description: A description of the changes
                - enhanced_guide: The complete guide with new content integrated
                - changes: List of changes describing what was modified
                
            Raises:
                RuntimeError: If the LLM service fails to generate content
            """
            print(f"Processing node: {source_node.title} (level {source_node.level})")
            
            # Construct the system prompt for the LLM
            system_prompt = f"""
You are an expert technical writer helping to create a quickstart guide for the Alloy Specification Language.
Your task is to analyze source content and integrate it into the current guide.

The guidance for authoring includes:
{author_guidance}
"""

            # Construct the user prompt for the LLM
            user_prompt = f"""
I'm working on a section of the guide titled "{source_node.title}".

Here's the source content:
```
{source_node.content}
```

Here's the current guide:
```
{current_guide}
```

Your task is to analyze the source content and determine if it should be integrated into the guide. You have four options:
1. ADD new content at an appropriate location in the guide
2. REMOVE existing content that is outdated or redundant
3. REPLACE existing content with improved content
4. SKIP if the source content is already adequately covered in the guide or isn't relevant

Please analyze the current guide and the source content, then provide:
1. A brief description of your decision (one line)
2. If not skipping, the complete updated guide with your changes integrated
3. A list of specific changes you made, each formatted as:
   - Operation (ADD, REMOVE, REPLACE, or SKIP)
   - Location (section title or paragraph that helps identify where the change occurs)
   - Content (the actual text being added, removed, or used as replacement; omit for SKIP)

Focus on maintaining a cohesive, well-structured document that clearly explains Alloy concepts.
You should choose SKIP if the content is:
- Already adequately covered in the guide
- Too advanced for a quickstart guide
- Not directly relevant to learning the basics of Alloy
- Better suited for a different section that will be handled separately
"""

            # Generate content using the LLM service - let any errors propagate
            completion = llm_service.complete(system_prompt, user_prompt)
            
            # Parse the LLM response
            sections = completion.split("\n\n", 1)
            if len(sections) > 1:
                description = sections[0].strip()
                
                # Check if this is a SKIP operation
                if "SKIP" in description.upper():
                    print(f"Skipping content from '{source_node.title}': {description}")
                    return description, current_guide, [{
                        "type": "SKIP",
                        "location": source_node.title,
                        "content": ""
                    }]
                
                content_sections = sections[1].split("Changes:", 1)
                
                if len(content_sections) > 1:
                    enhanced_guide = content_sections[0].strip()
                    changes_text = content_sections[1].strip()
                    
                    # Parse the changes
                    changes = []
                    change_blocks = re.finditer(
                        r"(ADD|REMOVE|REPLACE|SKIP):\s+([^\n]+)\s*(?:-\s*([^#]+))?", 
                        changes_text,
                        re.MULTILINE
                    )
                    
                    for match in change_blocks:
                        operation = match.group(1).strip()
                        location = match.group(2).strip()
                        content = match.group(3).strip() if match.group(3) else ""
                        
                        changes.append({
                            "type": operation,
                            "location": location,
                            "content": content
                        })
                        
                        # If we find a SKIP operation, return immediately with no changes
                        if operation == "SKIP":
                            print(f"Skipping content from '{source_node.title}': {description}")
                            return description, current_guide, [{
                                "type": "SKIP",
                                "location": location,
                                "content": ""
                            }]
                else:
                    # Couldn't parse changes section, use the entire content as the guide
                    enhanced_guide = sections[1].strip()
                    changes = [{
                        "type": "ADD", 
                        "location": source_node.title, 
                        "content": f"Content from {source_node.title}"
                    }]
            else:
                # Check if this is a simple SKIP response
                if "SKIP" in completion.upper():
                    print(f"Skipping content from '{source_node.title}': {completion.strip()}")
                    return completion.strip(), current_guide, [{
                        "type": "SKIP",
                        "location": source_node.title,
                        "content": ""
                    }]
                
                # Fallback if we couldn't parse the response
                description = f"Update from {source_node.title}"
                enhanced_guide = completion.strip()
                changes = [{
                    "type": "ADD", 
                    "location": source_node.title, 
                    "content": f"Content from {source_node.title}"
                }]
            
            # If there are no changes detected but content is different, add a default change
            if not changes and enhanced_guide != current_guide:
                changes = [{
                    "type": "ADD", 
                    "location": source_node.title, 
                    "content": f"Content from {source_node.title}"
                }]
            
            return description, enhanced_guide, changes


# -----------------------------------------------------------------------------
# Application Layer
# -----------------------------------------------------------------------------

class Application:
    """Namespace for application-level functionality."""
    
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
            """
            config = {
                "action": args.action,
                "source_file": args.source,
                "base_file": args.base,
                "patch_dir": args.patch_dir,
                "author_file": args.author_file,
            }
            
            # Process LLM configuration if provided
            llm_config = Application.Configuration.get_llm_config(args)
            if llm_config:
                config["llm"] = llm_config
                
            return config
        
        @staticmethod
        def get_llm_config(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
            """
            Extract LLM configuration from arguments or environment.
            
            Args:
                args: Parsed command-line arguments
                
            Returns:
                Dictionary with LLM configuration or None if not available
            """
            # Try to get values from args first, then environment variables
            endpoint = args.azure_endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
            api_key = args.azure_key or os.environ.get("AZURE_OPENAI_KEY")
            deployment = args.azure_deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
            
            # Create config if all required values are available
            if endpoint and api_key and deployment:
                return {
                    "endpoint": endpoint,
                    "api_key": api_key,
                    "deployment": deployment,
                    "max_retries": args.max_retries if hasattr(args, 'max_retries') else 3,
                    "retry_delay": args.retry_delay if hasattr(args, 'retry_delay') else 1.0,
                    "temperature": args.temperature if hasattr(args, 'temperature') else 0.7,
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
                "source_file": os.environ.get("ALLOY_SOURCE_FILE", "alloy_book.md"),
                "base_file": os.environ.get("ALLOY_BASE_FILE", "guide_base.md"),
                "patch_dir": os.environ.get("ALLOY_PATCH_DIR", "patches"),
                "author_file": os.environ.get("ALLOY_AUTHOR_FILE", "AUTHOR.md"),
            }
            
            return config
    
    class GuideGenerator:
        """Main class for generating the Alloy quickstart guide."""
        
        def __init__(
            self, 
            source_file: str, 
            base_file: str, 
            patch_dir: str, 
            author_file: str,
            llm_service: Optional[Utilities.LLMService] = None
        ) -> None:
            """
            Initialize the guide generator.
            
            Args:
                source_file: Path to the source markdown file
                base_file: Path to the base guide file
                patch_dir: Directory for storing patches
                author_file: Path to the author guidance file
                llm_service: Optional LLM service for content generation
            """
            self.source_file = source_file
            self.base_file = base_file
            self.patch_dir = patch_dir
            self.author_file = author_file
            self.llm_service = llm_service
            
            # Components to be initialized later
            self.markdown_tree: Optional[DocumentProcessing.Tree] = None
            self.version_manager: Optional[ContentManagement.VersionManager] = None
            self.author_guidance: str = ""
            
            # Load author guidance if file exists
            if Utilities.FileSystem.file_exists(author_file):
                self.author_guidance = Utilities.FileSystem.read_file(author_file)
            else:
                print(f"Warning: Author guidance file '{author_file}' not found.")
                self.author_guidance = "Create a clear, concise quickstart guide for the Alloy language."
        
        def initialize(self) -> None:
            """
            Initialize the generator components.
            
            Raises:
                RuntimeError: If initialization fails
            """
            try:
                # Parse the source file
                print(f"Parsing source file: {self.source_file}")
                self.markdown_tree = DocumentProcessing.Parser.parse_file(self.source_file)
                
                # Set up the version manager
                self.version_manager = ContentManagement.VersionManager(self.base_file, self.patch_dir)
                
                print("Initialization complete.")
            except Exception as e:
                raise RuntimeError(f"Initialization failed: {str(e)}") from e
        
        def render(self) -> str:
            """
            Render the current state of the guide.
            
            Returns:
                The rendered guide content
                
            Raises:
                RuntimeError: If rendering fails
            """
            # Initialize if needed
            if not self.version_manager:
                self.initialize()
                
            if not self.version_manager:
                raise RuntimeError("Failed to initialize version manager")
            
            # Render the guide
            return self.version_manager.render()
        
        def author(self) -> str:
            """
            Run the authoring process.
            
            Returns:
                Path to the output file
                
            Raises:
                RuntimeError: If authoring fails or LLM service is not available
            """
            # Check if LLM service is available
            if not self.llm_service:
                raise RuntimeError("LLM service is required for authoring")
                
            # Initialize if needed
            if not self.markdown_tree or not self.version_manager:
                self.initialize()
                
            if not self.markdown_tree or not self.version_manager:
                raise RuntimeError("Failed to initialize components")
            
            # Get the current state of the guide
            current_guide = self.version_manager.render()
            
            # Determine the next major iteration
            major_iteration = self._get_next_major_iteration()
            print(f"Starting major iteration {major_iteration}")
            
            # Traverse the markdown tree
            minor_iteration = 0
            patch_count = 0
            skipped_count = 0
            
            # Process each node in the tree
            for node, depth in self.markdown_tree.dfs_traversal():
                # Skip the root node
                if node == self.markdown_tree.root:
                    continue
                
                try:
                    print(f"\nProcessing node: {node.title} (level {node.level}, depth {depth})")
                    
                    # Generate content
                    description, enhanced_guide, changes = ContentManagement.ContentGenerator.generate_content(
                        node, current_guide, self.author_guidance, self.llm_service
                    )
                    
                    # Check if changes were skipped
                    if changes and changes[0].get("type") == "SKIP":
                        print(f"Skipped: {description}")
                        skipped_count += 1
                        minor_iteration += 1
                        continue
                    
                    # Create diff
                    diff_content = Utilities.DiffManager.create_diff(current_guide, enhanced_guide)
                    
                    # Create patch version
                    patch_version = f"{major_iteration}-{minor_iteration}-{patch_count}"
                    
                    # Add the patch
                    patch_file = self.version_manager.add_patch(
                        patch_version, description, diff_content, changes
                    )
                    print(f"Added patch: {patch_file}")
                    
                    patch_count += 1
                    
                    # Update current guide
                    current_guide = enhanced_guide
                    
                except Exception as e:
                    print(f"Error processing node '{node.title}': {str(e)}")
                
                # Increment minor iteration
                minor_iteration += 1
            
            # Save the complete iteration
            output_file = self.version_manager.save_iteration(major_iteration)
            print(f"\nMajor iteration {major_iteration} complete:")
            print(f"- Processed {minor_iteration} nodes")
            print(f"- Created {patch_count} patches")
            print(f"- Skipped {skipped_count} nodes")
            print(f"- Output saved to: {output_file}")
            
            return output_file
        
        def _get_next_major_iteration(self) -> int:
            """
            Determine the next major iteration number.
            
            Returns:
                Next major iteration number
            """
            # Look for existing guide files
            guide_files = [f for f in os.listdir(".") if f.startswith("guide-") and f.endswith(".md")]
            
            if not guide_files:
                return 1
            
            # Extract iteration numbers
            iterations = []
            for f in guide_files:
                match = re.search(r"guide-(\d+)\.md", f)
                if match and match.group(1).isdigit():
                    iterations.append(int(match.group(1)))
            
            return max(iterations) + 1 if iterations else 1
    
    @staticmethod
    def create_cli_parser() -> argparse.ArgumentParser:
        """
        Create the command-line interface parser.
        
        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(
            description="Generate an Alloy quickstart guide by iteratively processing source material.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Render the current state of the guide
  python alloy_guide_generator.py render

  # Run the authoring process
  python alloy_guide_generator.py author

Environment Variables:
  - AZURE_OPENAI_ENDPOINT: URL for Azure OpenAI endpoint
  - AZURE_OPENAI_KEY: API key for Azure OpenAI
  - AZURE_OPENAI_DEPLOYMENT: Deployment name in Azure
  - ALLOY_SOURCE_FILE: Path to source markdown file
  - ALLOY_BASE_FILE: Path to base guide file
  - ALLOY_PATCH_DIR: Directory for storing patches
  - ALLOY_AUTHOR_FILE: Path to author guidance file
"""
        )
        
        # Add action argument
        parser.add_argument(
            "action", 
            choices=["render", "author"],
            help="Action to perform: render the guide or run the authoring process"
        )
        
        # File and directory options
        parser.add_argument(
            "--source", "-s", 
            default="alloy_book.md",
            help="Source markdown file (default: alloy_book.md)"
        )
        
        parser.add_argument(
            "--base", "-b", 
            default="guide_base.md",
            help="Base guide file (default: guide_base.md)"
        )
        
        parser.add_argument(
            "--patch-dir", "-p", 
            default="patches",
            help="Directory for storing patches (default: patches)"
        )
        
        parser.add_argument(
            "--author-file", "-a", 
            default="AUTHOR.md",
            help="File containing authoring guidance (default: AUTHOR.md)"
        )
        
        # Azure OpenAI options
        parser.add_argument(
            "--azure-endpoint",
            help="Azure OpenAI API endpoint URL (or set AZURE_OPENAI_ENDPOINT env variable)"
        )
        
        parser.add_argument(
            "--azure-key",
            help="Azure OpenAI API key (or set AZURE_OPENAI_KEY env variable)"
        )
        
        parser.add_argument(
            "--azure-deployment",
            help="Azure OpenAI deployment name (or set AZURE_OPENAI_DEPLOYMENT env variable)"
        )
        
        parser.add_argument(
            "--temperature",
            type=float,
            default=0.7,
            help="Temperature for generation (0.0 to 1.0, default: 0.7)"
        )
        
        parser.add_argument(
            "--max-retries",
            type=int,
            default=3,
            help="Maximum number of retry attempts for API calls (default: 3)"
        )
        
        parser.add_argument(
            "--retry-delay",
            type=float,
            default=1.0,
            help="Base delay between retries in seconds (default: 1.0)"
        )
        
        return parser
    
    @staticmethod
    def main() -> None:
        """
        Main entry point for the application.
        
        This function:
        1. Parses command-line arguments
        2. Creates the appropriate components
        3. Performs the requested action
        4. Handles interactive mode for authoring
        """
        # Parse command-line arguments
        parser = Application.create_cli_parser()
        args = parser.parse_args()
        
        try:
            # Extract configuration from arguments
            config = Application.Configuration.from_args(args)
            
            # Create LLM service if configuration is available
            llm_service = None
            if "llm" in config:
                llm_config = config["llm"]
                llm_service = Utilities.AzureOpenAIService(
                    endpoint=llm_config["endpoint"],
                    api_key=llm_config["api_key"],
                    deployment_name=llm_config["deployment"],
                    api_version="2023-05-15",
                    max_retries=llm_config["max_retries"],
                    retry_delay=llm_config["retry_delay"]
                )
            
            # Create guide generator
            generator = Application.GuideGenerator(
                source_file=config["source_file"],
                base_file=config["base_file"],
                patch_dir=config["patch_dir"],
                author_file=config["author_file"],
                llm_service=llm_service
            )
            
            # Perform the requested action
            if config["action"] == "render":
                rendered_guide = generator.render()
                print(rendered_guide)
            elif config["action"] == "author":
                if not llm_service:
                    print("Error: LLM service is required for authoring.")
                    print("Please provide Azure OpenAI credentials via arguments or environment variables.")
                    return
                
                # Run authoring process
                generator.author()
                
                # Interactive mode
                while True:
                    response = input("\nContinue with next iteration? (y/n): ").lower()
                    if response == 'y':
                        generator.author()
                    else:
                        break
            
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


# -----------------------------------------------------------------------------
# Cross-Cutting Concerns
# -----------------------------------------------------------------------------

class Utilities:
    """Namespace for utility functions used across the application."""
    
    class LLMService(Protocol):
        """Protocol for language model service interactions."""
        
        def complete(
            self,
            system_prompt: str,
            user_prompt: str,
            max_tokens: int = 2000,
            temperature: float = 0.7
        ) -> str:
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
        
        def _send_request(
            self,
            url: str,
            data: dict,
            headers: dict,
            retry_count: int = 0
        ) -> dict:
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
                    delay = self.retry_delay * (2 ** retry_count) * (0.5 + random.random())
                    print(f"Request failed with {e.code}. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    return self._send_request(url, data, headers, retry_count + 1)
                else:
                    raise RuntimeError(error_msg) from e
                    
            except Exception as e:
                raise RuntimeError(f"Request failed: {str(e)}") from e
        
        def complete(
            self,
            system_prompt: str,
            user_prompt: str,
            max_tokens: int = 2000,
            temperature: float = 0.7
        ) -> str:
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
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Prepare the request URL
            url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
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
                
            files = [os.path.join(directory, f) for f in os.listdir(directory) 
                    if os.path.isfile(os.path.join(directory, f))]
            
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
            diff_lines = list(difflib.unified_diff(
                original.splitlines(),
                modified.splitlines(),
                fromfile="original",
                tofile="modified",
                lineterm=""
            ))
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
                return content  # No changes
            
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
                    
                    content_to_add = line[1:]  # Remove the + prefix
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
# Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    Application.main()