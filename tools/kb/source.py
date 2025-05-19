"""
# Knowledge Base Generator - Source Module

A module for processing source documents for knowledge base generation through
parsing, streaming, and structured representation.

This module handles:
- Document representation and metadata
- Stream-based document processing
- Markdown parsing and hierarchical structure
- Document tree construction and traversal
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------------------------------------------------------
# Document Processing Layer
# -----------------------------------------------------------------------------

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
    self.documents: List[Document] = []

  def read_all(self) -> str:
    """
        Read all content from the stream.
        
        Returns:
            The full content as a string
        """
    return self.content

  def get_documents(self) -> List[Document]:
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
      self.documents.append(Document("default", current_content))

    # Process the remaining parts (name, size, content, name, size, content, ...)
    i = 1
    while i < len(parts) - 2:
      doc_name = parts[i]
      try:
        doc_size = int(parts[i + 1])
      except ValueError:
        doc_size = 0
      doc_content = parts[i + 2].strip()

      self.documents.append(Document(doc_name, doc_content, doc_size))
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
      self.documents.append(Document("stdin", self.content, doc_size))
    else:
      # Parse document separators
      self._parse_document_separators(self.content)

class Node:

  """Represents a node in the markdown document tree."""

  def __init__(self, level: int, title: str, content: str = "", parent: Optional[Node] = None, document: Optional[Document] = None) -> None:
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
    self.parent: Optional[Node] = parent
    self.children: List[Node] = []
    self.document: Optional[Document] = document

  def add_child(self, child: Node) -> None:
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
    self.root: Node = Node(0, "ROOT")
    self.current: Node = self.root
    # Map of document names to subtrees
    self.document_roots: Dict[str, Node] = {}

  def add_node(self, level: int, title: str, content: str = "", document: Optional[Document] = None) -> Node:
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
    parent: Node = self.root
    node: Node = self.root

    # If this is the first node for a document, create a document root
    if document and document.name not in self.document_roots:
      # Create a document root node
      doc_root = Node(0, document.name, "", self.root, document)
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
    new_node = Node(level, title, content, parent, document)
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

  def dfs_traversal(self) -> List[Tuple[Node, int]]:
    """
        Perform a depth-first traversal of the tree, returning node and depth pairs.
        
        Returns:
            List of (node, depth) pairs
        """
    result: List[Tuple[Node, int]] = []

    def _dfs(node: Node, depth: int = 0) -> None:
      result.append((node, depth))
      for child in node.children:
        _dfs(child, depth + 1)

    _dfs(self.root)
    return result

  def get_nodes_by_document(self, document_name: str) -> List[Node]:
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

    def _collect_nodes(node: Node) -> None:
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
  def parse_stream(stream: MarkdownStream) -> Tree:
    """
        Parse a markdown stream into a tree structure.
        
        Args:
            stream: A markdown stream
                
        Returns:
            A tree representation of the markdown structure
                
        Raises:
            ParsingError: If there's an error parsing the stream
        """
    tree = Tree()

    # Process each document in the stream
    for document in stream.get_documents():
      MarkdownParser._parse_document(document, tree)

    # Validate the tree
    warnings = tree.validate()
    if warnings:
      # Just log warnings but don't fail
      print("Markdown parsing warnings:")
      for warning in warnings:
        print(f"- {warning}")

    return tree

  @staticmethod
  def _parse_document(document: Document, tree: Tree) -> None:
    """
        Parse a single document and add it to the tree.
        
        Args:
            document: The document to parse
            tree: The tree to add nodes to
            
        Raises:
            ParsingError: If there's an error parsing the document
        """
    lines = document.content.splitlines()
    current_node = None
    current_content: List[str] = []
    line_number = 0

    for line in lines:
      line_number += 1
      line = line.rstrip()
      header_match = MarkdownParser.HEADER_PATTERN.match(line)

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
          raise ParsingError(f"Empty header title at line {line_number} in document '{document.name}'")

        # Check for excessively deep header level
        if level > 6:
          raise ParsingError(f"Header level too deep (level {level}) at line {line_number} in document '{document.name}': {line}")

        current_node = tree.add_node(level, title, "", document)
      else:
        # Add this line to the accumulated content
        current_content.append(line)

    # Add any remaining content to the last node
    if current_content and current_node:
      current_node.content += "\n".join(current_content)

  @staticmethod
  def parse_files(file_paths: List[str]) -> Tree:
    """
        Parse multiple markdown files into a tree structure.
        
        Args:
            file_paths: List of paths to markdown files
                
        Returns:
            A tree representation of the markdown files
                
        Raises:
            ParsingError: If there's an error parsing any file
        """
    stream = FileMarkdownStream(file_paths)
    return MarkdownParser.parse_stream(stream)

  @staticmethod
  def parse_stdin(is_concat_stream: bool = False) -> Tree:
    """
        Parse markdown from standard input into a tree structure.
        
        Args:
            is_concat_stream: Whether the input is already a concatenated stream
                            with document separators
                
        Returns:
            A tree representation of the markdown from stdin
                
        Raises:
            ParsingError: If there's an error parsing the input
        """
    stream = StdinMarkdownStream(is_concat_stream)
    return MarkdownParser.parse_stream(stream)

# -----------------------------------------------------------------------------
# Application Layer - Source Command
# -----------------------------------------------------------------------------

class Application:

  """Handles application-level functionality for source document operations."""

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
        raise IOError(f"Error reading {file_path}: {str(e)}")

  @staticmethod
  def create_cli_parser() -> Any: # argparse.ArgumentParser
    """
        Create the command-line interface parser for source document operations.
        
        Returns:
            Configured argument parser
        """
    import argparse

    parser = argparse.ArgumentParser(
      description="Process source documents for knowledge base generation.",
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog="""
Examples:
  # Concatenate multiple files and output to stdout
  python -m tools.kb.source concat file1.md file2.md > combined.md

  # Concatenate multiple files and output to a file
  python -m tools.kb.source concat file1.md file2.md -o combined.md

  # Validate the structure of markdown files
  python -m tools.kb.source validate file1.md file2.md
""")

    # Add action argument
    parser.add_argument("action", choices=["concat", "validate"], help="Action to perform: concatenate files or validate source")

    # Add file arguments
    parser.add_argument("files", nargs="+", help="List of markdown files to process")

    # Output options
    parser.add_argument("--output-file", "-o", help="Output file path (stdout if not specified)")

    return parser

  @staticmethod
  def main() -> None:
    """
        Main entry point for the source document application.
        
        This function:
        1. Parses command-line arguments
        2. Creates the appropriate components
        3. Performs the requested action
        """
    import argparse

    # Parse command-line arguments
    parser = Application.create_cli_parser()
    args = parser.parse_args()

    try:
      if args.action == "concat":
        # Get output file handle if specified
        output_file = None
        if args.output_file:
          output_file = open(args.output_file, 'w', encoding='utf-8')

        try:
          # Process files incrementally
          Application.concat_files(args.files, output_file)
        finally:
          # Close output file if we opened one
          if output_file:
            output_file.close()

      elif args.action == "validate":
        # Parse and validate the documents
        tree = MarkdownParser.parse_files(args.files)
        warnings = tree.validate()

        if warnings:
          print("Validation warnings:")
          for warning in warnings:
            print(f"- {warning}")
        else:
          print("Documents validated successfully. No issues found.")

    except (ValueError, FileNotFoundError, IOError) as e:
      print(f"Error: {str(e)}", file=sys.stderr)
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
