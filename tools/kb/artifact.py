"""
# Knowledge Base Generator - Artifact Module

A module for managing knowledge base artifacts through content management,
template handling, and versioning systems.

This module handles:
- Template management for content generation
- Guidance parameters for content styling
- Content selection based on rules
- Patch-based versioning for incremental updates
- Content generation via LLM integration
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Protocol, Self, Tuple, TypedDict, cast

# Will be imported from other modules once they're created
from ._core.errors import ConfigurationError
from ._utils.filesystem import FileSystem
from ._utils.diff import DiffManager
from ._utils.llm import LLMService

# Will be imported from the source module once it's created
# For now define a placeholder to maintain type hints
class DocumentNode:

  """Placeholder for the DocumentNode class from the source module."""
  level: int
  title: str
  content: str
  parent: Optional["DocumentNode"]
  children: List["DocumentNode"]
  document: Optional[Any]

  def add_child(self, child: "DocumentNode") -> None:
    ...

  def add_content(self, content: str) -> None:
    ...

  def is_empty(self) -> bool:
    ...

# -----------------------------------------------------------------------------
# Content Management Layer
# -----------------------------------------------------------------------------

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
            TemplateError: If formatting fails
        """
    try:
      return self.system_template.format(**kwargs)
    except KeyError as e:
      raise TemplateError(f"Missing parameter for system template: {e}")
    except Exception as e:
      raise TemplateError(f"Error formatting system template: {e}")

  def format_user_prompt(self, **kwargs) -> str:
    """
        Format the user prompt template with provided values.
        
        Args:
            **kwargs: Key-value pairs to substitute in the template
            
        Returns:
            Formatted user prompt
            
        Raises:
            TemplateError: If formatting fails
        """
    try:
      return self.user_template.format(**kwargs)
    except KeyError as e:
      raise TemplateError(f"Missing parameter for user template: {e}")
    except Exception as e:
      raise TemplateError(f"Error formatting user template: {e}")

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
    self.templates: Dict[str, PromptTemplate] = {
      "default": PromptTemplate(system_template=self.DEFAULT_SYSTEM_TEMPLATE, user_template=self.DEFAULT_USER_TEMPLATE)
    }

  def add_template(self, name: str, system_template: str, user_template: str) -> None:
    """
        Add a new prompt template.
        
        Args:
            name: Template identifier
            system_template: System prompt template
            user_template: User prompt template
            
        Raises:
            TemplateError: If the template name already exists
        """
    if name in self.templates:
      raise TemplateError(f"Template '{name}' already exists")

    self.templates[name] = PromptTemplate(system_template=system_template, user_template=user_template)

  def get_template(self, name: str = "default") -> PromptTemplate:
    """
        Get a prompt template by name.
        
        Args:
            name: Template identifier
            
        Returns:
            The requested template
            
        Raises:
            TemplateError: If the template name doesn't exist
        """
    if name not in self.templates:
      raise TemplateError(f"Template '{name}' not found")
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
            TemplateError: If there's an error loading templates
        """
    try:
      with open(filepath, 'r', encoding='utf-8') as f:
        templates_data = json.load(f)

      loaded_templates = []
      for name, template_data in templates_data.items():
        if not isinstance(template_data, dict):
          raise TemplateError(f"Invalid template data for '{name}'")

        system_template = template_data.get("system_template")
        user_template = template_data.get("user_template")

        if not system_template or not user_template:
          raise TemplateError(f"Missing template content for '{name}'")

        self.add_template(name, system_template, user_template)
        loaded_templates.append(name)

      return loaded_templates

    except json.JSONDecodeError:
      raise TemplateError(f"Invalid JSON format in template file: {filepath}")
    except Exception as e:
      if not isinstance(e, TemplateError):
        raise TemplateError(f"Error loading template file: {str(e)}")
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
            GuidanceError: If the guidance name already exists
        """
    if name in self.guidance:
      raise GuidanceError(f"Guidance '{name}' already exists")

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
            GuidanceError: If the guidance name doesn't exist
        """
    if name not in self.guidance:
      raise GuidanceError(f"Guidance '{name}' not found")
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
            GuidanceError: If there's an error loading guidance
        """
    try:
      with open(filepath, 'r', encoding='utf-8') as f:
        guidance_data = json.load(f)

      loaded_guidance = []
      for name, parameters in guidance_data.items():
        if not isinstance(parameters, dict):
          raise GuidanceError(f"Invalid guidance data for '{name}'")

        self.add_guidance(name, parameters)
        loaded_guidance.append(name)

      return loaded_guidance

    except json.JSONDecodeError:
      raise GuidanceError(f"Invalid JSON format in guidance file: {filepath}")
    except Exception as e:
      if not isinstance(e, GuidanceError):
        raise GuidanceError(f"Error loading guidance file: {str(e)}")
      raise

class ContentSelector:

  """Selects content from source nodes based on configured rules."""

  def __init__(self) -> None:
    """Initialize the content selector with no rules."""
    self.rules: List[ContentSelectionRule] = []

  def add_rule(self, rule: "ContentSelectionRule") -> None:
    """
        Add a content selection rule.
        
        Args:
            rule: The rule to add
        """
    self.rules.append(rule)
    # Sort rules by priority (descending)
    self.rules.sort(key=lambda r: r.priority, reverse=True)

  def should_include(self, node: DocumentNode) -> bool:
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

  def filter_nodes(self, nodes: List[DocumentNode]) -> List[DocumentNode]:
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

  def __init__(self, name: str, condition: Callable[[DocumentNode], bool], priority: int = 0) -> None:
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

  def applies_to(self, node: DocumentNode) -> bool:
    """
        Check if this rule applies to a node.
        
        Args:
            node: The node to evaluate
            
        Returns:
            True if the rule applies, False otherwise
        """
    return self.condition(node)

def create_header_level_rule(max_level: int) -> ContentSelectionRule:
  """
    Create a rule that includes nodes up to a specified header level.
    
    Args:
        max_level: Maximum header level to include (1-6)
        
    Returns:
        ContentSelectionRule that includes nodes with level <= max_level
    """
  return ContentSelectionRule(name=f"header_level_max_{max_level}", condition=lambda node: node.level <= max_level, priority=100)

def create_keyword_rule(keywords: List[str], case_sensitive: bool = False) -> ContentSelectionRule:
  """
    Create a rule that includes nodes containing specified keywords.
    
    Args:
        keywords: List of keywords to match
        case_sensitive: Whether to use case-sensitive matching
        
    Returns:
        ContentSelectionRule that includes nodes with matching keywords
    """

  def has_keywords(node: DocumentNode) -> bool:
    text = node.title + "\n" + node.content
    for keyword in keywords:
      if case_sensitive:
        if keyword in text:
          return True
      else:
        if keyword.lower() in text.lower():
          return True
    return False

  return ContentSelectionRule(name=f"keywords_{','.join(keywords)}", condition=has_keywords, priority=50)

def create_regex_rule(pattern: str) -> ContentSelectionRule:
  """
    Create a rule that includes nodes matching a regex pattern.
    
    Args:
        pattern: Regular expression pattern to match
        
    Returns:
        ContentSelectionRule that includes nodes matching the pattern
    """
  regex = re.compile(pattern)

  def matches_pattern(node: DocumentNode) -> bool:
    text = node.title + "\n" + node.content
    return bool(regex.search(text))

  return ContentSelectionRule(name=f"regex_{pattern}", condition=matches_pattern, priority=75)

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
    FileSystem.ensure_directory(patch_dir)

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
    FileSystem.write_file(filename, "\n".join(content))
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
    content = FileSystem.read_file(filename)

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
    self.patches: List[Patch] = []

    # Ensure patch directory exists
    FileSystem.ensure_directory(patch_dir)

    # Load base file if it exists
    if FileSystem.file_exists(base_file):
      self.base_content = FileSystem.read_file(base_file)

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
    patch_files = FileSystem.list_files(self.patch_dir, r"^patch-.*\.md$")

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
        patch = Patch.from_file(patch_file)
        self.patches.append(patch)
      except Exception as e:
        print(f"Error loading patch {patch_file}: {e}")

  def parse_version(self, version: str) -> Version:
    """
        Parse a version string into its components.
        
        Args:
            version: Version string in format "major-minor-patch"
            
        Returns:
            Dictionary containing major, minor, and patch values
        """
    parts = version.split("-")
    result: Version = {"major": 0, "minor": 0, "patch": 0}

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
      # Apply the patch using DiffManager
      try:
        current_content = DiffManager.apply_diff(current_content, patch.diff_content)
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
    patch = Patch(version, description, diff_content, changes)
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
    FileSystem.write_file(output_file, content)
    return output_file

class ContentGenerator:

  """Generates content using LLM integration."""

  def __init__(
      self,
      llm_service: LLMService,
      template_manager: Optional[TemplateManager] = None,
      guidance_manager: Optional[GuidanceManager] = None,
      context_window_manager: Optional[SimpleContextWindowManager] = None) -> None:
    """
        Initialize the content generator.
        
        Args:
            llm_service: Service for language model interactions
            template_manager: Manager for prompt templates
            guidance_manager: Manager for guidance parameters
            context_window_manager: Manager for context window size constraints
        """
    self.llm_service = llm_service
    self.template_manager = template_manager or TemplateManager()
    self.guidance_manager = guidance_manager or GuidanceManager()
    self.context_window_manager = context_window_manager or SimpleContextWindowManager()

  def generate_content(
      self,
      source_node: DocumentNode,
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
            ContentGenerationError: If content generation fails
            TemplateError: If the template name doesn't exist
            GuidanceError: If the guidance name doesn't exist
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
      if isinstance(e, (TemplateError, GuidanceError)):
        raise
      raise ContentGenerationError(f"Content generation failed: {str(e)}") from e

  def _parse_completion(self, completion: str, source_node: DocumentNode, current_article: str) -> Tuple[str, str, List[Dict[str, str]]]:
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
# Application Layer - Artifact Command
# -----------------------------------------------------------------------------

class Application:

  """Handles application-level functionality for artifact operations."""

  class KnowledgeBaseGenerator:

    """Main class for generating knowledge base articles."""

    def __init__(
        self,
        config: Dict[str, Any],
        content_generator: Optional[ContentGenerator] = None,
        template_manager: Optional[TemplateManager] = None,
        guidance_manager: Optional[GuidanceManager] = None) -> None:
      """
            Initialize the knowledge base generator.
            
            Args:
                config: Application configuration
                content_generator: Optional content generator
                template_manager: Optional template manager
                guidance_manager: Optional guidance manager
                
            Raises:
                ConfigurationError: If the configuration is invalid
            """
      self.config = config
      self.template_manager = template_manager or TemplateManager()
      self.guidance_manager = guidance_manager or GuidanceManager()

      # Initialize components based on configuration
      self._initialize_components()

      # Content generator will be initialized when needed
      self.content_generator = content_generator

    def _initialize_components(self) -> None:
      """
            Initialize components based on configuration.
            
            Raises:
                ConfigurationError: If component initialization fails
            """
      try:
        # Load templates if specified
        if "template" in self.config and "file" in self.config["template"]:
          template_file = self.config["template"]["file"]
          if template_file:
            try:
              loaded_templates = self.template_manager.load_template_file(template_file)
              print(f"Loaded templates: {', '.join(loaded_templates)}")
            except TemplateError as e:
              print(f"Warning: Failed to load templates: {str(e)}")

        # Load guidance if specified
        if "guidance" in self.config:
          if "file" in self.config["guidance"] and self.config["guidance"]["file"]:
            try:
              loaded_guidance = self.guidance_manager.load_guidance_file(self.config["guidance"]["file"])
              print(f"Loaded guidance profiles: {', '.join(loaded_guidance)}")
            except GuidanceError as e:
              print(f"Warning: Failed to load guidance: {str(e)}")
          elif "inline" in self.config["guidance"]:
            # Add inline guidance
            self.guidance_manager.add_guidance("inline", self.config["guidance"]["inline"])
      except Exception as e:
        raise ConfigurationError(f"Failed to initialize components: {str(e)}")

    def _get_content_selector(self) -> ContentSelector:
      """
            Create a content selector based on configuration.
            
            Returns:
                Configured content selector
            """
      selector = ContentSelector()

      # Add header level rule if specified
      max_header_level = self.config["processing"].get("max_header_level")
      if max_header_level is not None and 1 <= max_header_level <= 6:
        selector.add_rule(create_header_level_rule(max_header_level))

      # Add other rules based on configuration
      # (This would be expanded based on available configuration options)

      return selector

    def _initialize_content_generator(self, llm_service: LLMService) -> None:
      """
            Initialize the content generator.
            
            Args:
                llm_service: LLM service for content generation
            """
      if self.content_generator is None:
        self.content_generator = ContentGenerator(llm_service, self.template_manager, self.guidance_manager)

    def _get_llm_service(self) -> LLMService:
      """
            Create an LLM service based on configuration.
            
            Returns:
                Configured LLM service
                
            Raises:
                ConfigurationError: If the LLM configuration is invalid
            """
      try:
        if "llm" not in self.config:
          # This would be imported from _utils.llm
          from ._utils.llm import MockLLMService
          return MockLLMService()

        # This implementation will be updated when _utils.llm is created
        # For now, it's a placeholder to maintain type hints
        return cast(LLMService, None)

      except Exception as e:
        raise ConfigurationError(f"Failed to create LLM service: {str(e)}")

    def generate(self) -> str:
      """
            Generate a knowledge base article based on configuration.
            
            Returns:
                The generated article content
                
            Raises:
                ConfigurationError: If generation fails due to configuration issues
            """
      # This implementation will be completed when source module is created
      # For now, it's a placeholder to maintain the API
      return "Article content placeholder"

    def render(self) -> str:
      """
            Render the current state of the document by applying all patches.
            
            Returns:
                The document content with all patches applied
                
            Raises:
                ValueError: If a patch can't be applied cleanly
                ConfigurationError: If configuration is invalid
            """
      try:
        base_file = self.config["render"].get("base_file", "base.md")
        patch_dir = self.config["render"].get("patch_dir", "patches")

        # Create version manager
        version_manager = VersionManager(base_file, patch_dir)

        # Render the document
        content = version_manager.render()

        # Save to file if specified
        output_file = self.config["output"].get("file")
        if output_file:
          FileSystem.write_file(output_file, content)
          print(f"Output saved to: {output_file}")

        return content

      except Exception as e:
        if not isinstance(e, ConfigurationError):
          raise ConfigurationError(f"Rendering failed: {str(e)}")
        raise

  @staticmethod
  def create_cli_parser() -> argparse.ArgumentParser:
    """
        Create the command-line interface parser for artifact operations.
        
        Returns:
            Configured argument parser
        """
    parser = argparse.ArgumentParser(
      description="Manage knowledge base artifact content, templates, and versioning.",
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog="""
Examples:
  # Render patches to produce an article
  python -m .artifact render --base-file base.md --patch-dir patches --output-file article.md

  # Use custom templates
  python -m .artifact render --template-file templates.json --template-name technical

Environment Variables:
  - AZURE_OPENAI_ENDPOINT: URL for Azure OpenAI endpoint
  - AZURE_OPENAI_KEY: API key for Azure OpenAI
  - AZURE_OPENAI_DEPLOYMENT: Deployment name in Azure
  - KB_OUTPUT_FORMAT: Output format (markdown, html)
  - KB_OUTPUT_FILE: Output file path
  - KB_GUIDANCE_NAME: Guidance profile name
  - KB_GUIDANCE_FILE: Path to guidance JSON file
  - KB_TEMPLATE_NAME: Template name
  - KB_TEMPLATE_FILE: Path to template JSON file
""")

    # Add action argument
    parser.add_argument("action", choices=["render"], help="Action to perform: render patches into a complete document")

    # Output options
    parser.add_argument("--output-format", choices=["markdown", "html"], default="markdown", help="Output format (default: markdown)")
    parser.add_argument("--output-file", "-o", help="Output file path (stdout if not specified)")

    # Guidance options
    parser.add_argument("--guidance-file", help="Path to JSON file containing guidance profiles")
    parser.add_argument("--guidance-name", help="Name of guidance profile to use (default: default)")
    parser.add_argument("--guidance-inline", help="Inline guidance parameters (format: style=value,audience=value,...)")

    # Template options
    parser.add_argument("--template-file", help="Path to JSON file containing prompt templates")
    parser.add_argument("--template-name", help="Name of template to use (default: default)")

    # Version control options (for render action)
    parser.add_argument("--base-file", help="Base file for patch application (for render action)")
    parser.add_argument("--patch-dir", help="Directory containing patches (for render action)")

    return parser

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
            ConfigurationError: If the format is invalid
        """
    guidance_params = {}

    try:
      pairs = guidance_str.split(",")
      for pair in pairs:
        key, value = pair.split("=", 1)
        guidance_params[key.strip()] = value.strip()
    except ValueError:
      raise ConfigurationError(f"Invalid guidance parameter format: {guidance_str}")

    # Validate required parameters
    required_params = ["style", "audience", "structure", "formatting", "constraints"]
    missing_params = [param for param in required_params if param not in guidance_params]

    if missing_params:
      raise ConfigurationError(f"Missing guidance parameters: {', '.join(missing_params)}")

    return guidance_params

  @staticmethod
  def from_args(args: argparse.Namespace) -> Dict[str, Any]:
    """
        Create configuration from command-line arguments.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Dictionary containing configuration values
            
        Raises:
            ConfigurationError: If the configuration is invalid
        """
    try:
      config = {
        "action": args.action,
        "output": {
          "format": args.output_format,
          "file": args.output_file,
        },
        "processing": {
          "max_header_level": 6, # Default value
        }
      }

      # Handle guidance parameters
      if args.guidance_file:
        config["guidance"] = {"file": args.guidance_file, "name": args.guidance_name or "default"}
      elif args.guidance_inline:
        # Parse inline guidance parameters
        guidance_params = Application._parse_inline_guidance(args.guidance_inline)
        config["guidance"] = {"inline": guidance_params, "name": "inline"}
      else:
        config["guidance"] = {"name": args.guidance_name or "default"}

      # Handle template parameters
      if args.template_file:
        config["template"] = {"file": args.template_file, "name": args.template_name or "default"}
      else:
        config["template"] = {"name": args.template_name or "default"}

      # Process patch/render configuration if provided
      if args.action == "render":
        config["render"] = {"base_file": args.base_file or "base.md", "patch_dir": args.patch_dir or "patches"}

      return config

    except Exception as e:
      if not isinstance(e, ConfigurationError):
        raise ConfigurationError(f"Failed to create configuration: {str(e)}")
      raise

  @staticmethod
  def main() -> None:
    """
        Main entry point for the artifact application.
        
        This function:
        1. Parses command-line arguments
        2. Creates the appropriate components
        3. Performs the requested action
        """
    # Parse command-line arguments
    parser = Application.create_cli_parser()
    args = parser.parse_args()

    try:
      # Extract full configuration
      config = Application.from_args(args)

      # Create knowledge base generator
      generator = Application.KnowledgeBaseGenerator(config)

      # Perform the requested action
      if config["action"] == "render":
        output = generator.render()

        # Print to stdout if no output file specified
        if not config["output"].get("file"):
          print(output)

    except ConfigurationError as e:
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
