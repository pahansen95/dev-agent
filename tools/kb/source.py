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
import time
from typing import Any, Dict, List, Optional, Tuple

from ._utils.logger import get_logger, add_log_context

# Get a logger for this module
logger = get_logger(__name__)
logger.debug("Initializing source processing module")

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
    logger.debug(f"Creating document: {name}")
    self.name = name
    self.content = content
    self.size = size if size > 0 else len(content.encode('utf-8'))
    logger.debug(f"Document '{name}' created, size: {self.size} bytes")

  def __repr__(self) -> str:
    """Return string representation of the document."""
    return f"Document(name='{self.name}', size={self.size} bytes)"

class MarkdownStream:

  """Base class for markdown streams."""

  DOC_SEPARATOR_PATTERN = re.compile(r'<!-- DOC name="([^"]+)" size_of=(\d+) -->')

  def __init__(self) -> None:
    """Initialize the markdown stream."""
    logger.debug("Initializing MarkdownStream")
    self.content = "" # Full stream content
    self.documents: List[Document] = []

  def read_all(self) -> str:
    """
        Read all content from the stream.
        
        Returns:
            The full content as a string
        """
    logger.trace(f"Reading all content from stream, size: {len(self.content)} bytes")
    return self.content

  def get_documents(self) -> List[Document]:
    """
        Get all documents parsed from the stream.
        
        Returns:
            List of Document objects
        """
    logger.trace(f"Getting documents from stream, count: {len(self.documents)}")
    return self.documents

  def _parse_document_separators(self, content: str) -> None:
    """
        Parse document separators in the stream content.
        
        Args:
            content: The stream content to parse
        """
    logger.debug("Parsing document separators from stream content")
    logger.trace(f"Content size: {len(content)} bytes")

    # Split content by document separators
    parts = self.DOC_SEPARATOR_PATTERN.split(content)
    logger.trace(f"Split content into {len(parts)} parts")

    # First part is either empty or content before the first separator
    current_content = parts[0].strip()

    # If there's content before the first separator, treat it as a default document
    if current_content:
      logger.debug("Found content before first separator, creating default document")
      self.documents.append(Document("default", current_content))

    # Process the remaining parts (name, size, content, name, size, content, ...)
    i = 1
    doc_count = 0
    while i < len(parts) - 2:
      doc_name = parts[i]
      try:
        doc_size = int(parts[i + 1])
      except ValueError:
        logger.warning(f"Invalid document size for '{doc_name}', defaulting to 0")
        doc_size = 0
      doc_content = parts[i + 2].strip()

      logger.debug(f"Creating document from separator: {doc_name} ({doc_size} bytes)")
      self.documents.append(Document(doc_name, doc_content, doc_size))
      doc_count += 1
      i += 3

    logger.debug(f"Parsed {doc_count} documents from stream")

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
    logger.info(f"Creating FileMarkdownStream from {len(file_paths)} files")
    logger.debug(f"File paths: {', '.join(file_paths)}")
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
    logger.debug("Loading content from files")

    for file_path in self.file_paths:
      logger.debug(f"Reading file: {file_path}")
      try:
        start_time = time.time()
        with open(file_path, 'r', encoding='utf-8') as f:
          file_content = f.read()
          file_size = len(file_content.encode('utf-8'))
        elapsed_time = time.time() - start_time

        logger.debug(f"Read {file_size} bytes from {file_path} in {elapsed_time:.4f}s")

        # Add document separator before file content
        separator = f'<!-- DOC name="{os.path.basename(file_path)}" size_of={file_size} -->'
        combined_content.append(separator)
        combined_content.append(file_content)

      except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
      except Exception as e:
        logger.error(f"Error reading {file_path}: {str(e)}", exc_info=True)
        raise IOError(f"Error reading {file_path}: {str(e)}")

    # Store the combined content
    self.content = "\n\n".join(combined_content)
    logger.debug(f"Combined content size: {len(self.content)} bytes")

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
    logger.info(f"Creating StdinMarkdownStream, concat_stream={is_concat_stream}")
    self.is_concat_stream = is_concat_stream
    self._load_from_stdin()

  def _load_from_stdin(self) -> None:
    """Load content from standard input and parse document separators."""
    logger.debug("Loading content from stdin")

    # Read all content from stdin
    start_time = time.time()
    self.content = sys.stdin.read()
    elapsed_time = time.time() - start_time

    content_size = len(self.content)
    logger.debug(f"Read {content_size} bytes from stdin in {elapsed_time:.4f}s")

    # If not a concat stream, wrap in a document separator
    if not self.is_concat_stream:
      # Treat as a single document
      logger.debug("Not a concat stream, creating a single document")
      doc_size = len(self.content.encode('utf-8'))
      self.documents.append(Document("stdin", self.content, doc_size))
    else:
      # Parse document separators
      logger.debug("Parsing document separators from stdin content")
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

    parent_title = parent.title if parent else "None"
    doc_name = document.name if document else "None"
    logger.trace(f"Created node: level={level}, title='{title}', parent='{parent_title}', doc='{doc_name}'")

  def add_child(self, child: Node) -> None:
    """
        Add a child node to this node.
        
        Args:
            child: The child node to add
        """
    logger.trace(f"Adding child '{child.title}' to node '{self.title}'")
    child.parent = self
    self.children.append(child)

  def add_content(self, content: str) -> None:
    """
        Append content to this node.
        
        Args:
            content: The content to append
        """
    logger.trace(f"Adding content to node '{self.title}', size: {len(content)} bytes")
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
    is_empty = not self.content.strip() and not self.children
    logger.trace(f"Checked if node '{self.title}' is empty: {is_empty}")
    return is_empty

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
    logger.debug("Initializing document tree")
    self.root: Node = Node(0, "ROOT")
    self.current: Node = self.root
    # Map of document names to subtrees
    self.document_roots: Dict[str, Node] = {}
    logger.debug("Document tree initialized with root node")

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
    doc_name = document.name if document else "None"
    logger.debug(f"Adding node: level={level}, title='{title}', doc='{doc_name}'")

    # Find the appropriate parent for this node
    parent: Node = self.root
    node: Node = self.root

    # If this is the first node for a document, create a document root
    if document and document.name not in self.document_roots:
      # Create a document root node
      logger.debug(f"Creating document root node for '{document.name}'")
      doc_root = Node(0, document.name, "", self.root, document)
      self.root.add_child(doc_root)
      self.document_roots[document.name] = doc_root
      parent = doc_root
      node = doc_root
    elif document and document.name in self.document_roots:
      # Use existing document root
      logger.trace(f"Using existing document root for '{document.name}'")
      parent = self.document_roots[document.name]
      node = parent

    # Traverse up the tree until we find a node with a lower level
    while node.level >= level and node.parent is not None:
      logger.trace(f"Moving up tree from node '{node.title}' (level {node.level}) to find parent for level {level}")
      node = node.parent

    parent = node
    logger.trace(f"Found parent node: '{parent.title}' (level {parent.level})")

    # Create and add the new node
    new_node = Node(level, title, content, parent, document)
    parent.add_child(new_node)
    self.current = new_node

    logger.debug(f"Added node '{title}' (level {level}) to parent '{parent.title}' (level {parent.level})")
    return new_node

  def add_content_to_current(self, content: str) -> None:
    """
        Add content to the current node.
        
        Args:
            content: The content to add
        """
    if self.current != self.root:
      logger.trace(f"Adding content to current node '{self.current.title}', size: {len(content)} bytes")
      self.current.add_content(content)
    else:
      logger.warning("Attempted to add content to root node, ignoring")

  def dfs_traversal(self) -> List[Tuple[Node, int]]:
    """
        Perform a depth-first traversal of the tree, returning node and depth pairs.
        
        Returns:
            List of (node, depth) pairs
        """
    logger.debug("Performing depth-first traversal of document tree")
    result: List[Tuple[Node, int]] = []

    def _dfs(node: Node, depth: int = 0) -> None:
      result.append((node, depth))
      for child in node.children:
        _dfs(child, depth + 1)

    _dfs(self.root)
    logger.debug(f"Traversal completed, visited {len(result)} nodes")
    return result

  def get_nodes_by_document(self, document_name: str) -> List[Node]:
    """
        Get all nodes belonging to a specific document.
        
        Args:
            document_name: Name of the document
            
        Returns:
            List of nodes in the document
        """
    logger.debug(f"Getting nodes for document: '{document_name}'")

    if document_name not in self.document_roots:
      logger.warning(f"Document '{document_name}' not found in tree")
      return []

    result = []
    doc_root = self.document_roots[document_name]

    def _collect_nodes(node: Node) -> None:
      if node != doc_root: # Skip the document root itself
        result.append(node)
      for child in node.children:
        _collect_nodes(child)

    _collect_nodes(doc_root)
    logger.debug(f"Found {len(result)} nodes for document '{document_name}'")
    return result

  def validate(self) -> List[str]:
    """
        Validate the tree structure and content.
        
        Returns:
            A list of validation warnings, empty if no issues found
        """
    logger.info("Validating document tree structure")
    warnings = []

    # Validate each node in the tree
    node_count = 0
    for node, depth in self.dfs_traversal():
      node_count += 1
      # Skip root node and document root nodes
      if node == self.root or node.level == 0:
        continue

      # Check for empty nodes
      if node.is_empty():
        warning = f"Empty node found: '{node.title}'"
        logger.warning(warning)
        warnings.append(warning)

      # Check for invalid level jumps (e.g., h1 -> h3)
      if node.parent and node.parent.level > 0: # Skip root and doc roots
        if node.level > node.parent.level + 1:
          warning = f"Header level jump from {node.parent.level} to {node.level} " \
                    f"at node '{node.title}'"
          logger.warning(warning)
          warnings.append(warning)

    logger.info(f"Validation completed: {len(warnings)} warnings found in {node_count} nodes")
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
    logger.info("Parsing markdown stream")
    add_log_context("operation", "parse_stream")

    start_time = time.time()
    tree = Tree()

    # Process each document in the stream
    doc_count = len(stream.get_documents())
    logger.debug(f"Processing {doc_count} documents from stream")

    for i, document in enumerate(stream.get_documents(), 1):
      logger.debug(f"Parsing document {i}/{doc_count}: '{document.name}' ({document.size} bytes)")
      add_log_context("document", document.name)
      try:
        MarkdownParser._parse_document(document, tree)
      except Exception as e:
        logger.error(f"Error parsing document '{document.name}': {str(e)}", exc_info=True)
        raise
      finally:
        add_log_context("document", None)

    # Validate the tree
    warnings = tree.validate()
    if warnings:
      # Log warnings but don't fail
      logger.warning(f"Markdown parsing completed with {len(warnings)} warnings")
      for warning in warnings:
        logger.warning(f"Parse warning: {warning}")
    else:
      logger.info("Markdown parsing completed successfully, no warnings")

    elapsed_time = time.time() - start_time
    logger.info(f"Stream parsing completed in {elapsed_time:.4f}s")
    add_log_context("operation", None)

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
    logger.debug(f"Parsing document content: '{document.name}'")

    lines = document.content.splitlines()
    current_node = None
    current_content: List[str] = []
    line_number = 0
    header_count = 0

    logger.trace(f"Document has {len(lines)} lines")

    for line in lines:
      line_number += 1
      line = line.rstrip()
      header_match = MarkdownParser.HEADER_PATTERN.match(line)

      if header_match:
        header_count += 1
        logger.trace(f"Found header at line {line_number}: {line}")

        # If we have accumulated content, add it to the current node
        if current_content and current_node:
          current_node.add_content("\n".join(current_content))
          logger.trace(f"Added {len(current_content)} lines to node: '{current_node.title}'")
          current_content = []

        # Create a new node for this header
        level = len(header_match.group(1))
        title = header_match.group(2)

        # Check for empty title
        if not title.strip():
          error_msg = f"Empty header title at line {line_number} in document '{document.name}'"
          logger.error(error_msg)
          raise ParsingError(error_msg)

        # Check for excessively deep header level
        if level > 6:
          error_msg = f"Header level too deep (level {level}) at line {line_number} in document '{document.name}': {line}"
          logger.error(error_msg)
          raise ParsingError(error_msg)

        current_node = tree.add_node(level, title, "", document)
      else:
        # Add this line to the accumulated content
        current_content.append(line)

    # Add any remaining content to the last node
    if current_content and current_node:
      logger.trace(f"Adding remaining {len(current_content)} lines to node: '{current_node.title}'")
      current_node.add_content("\n".join(current_content))

    logger.debug(f"Completed parsing document: '{document.name}' - {header_count} headers found")

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
    logger.info(f"Parsing {len(file_paths)} markdown files")
    add_log_context("operation", "parse_files")

    try:
      stream = FileMarkdownStream(file_paths)
      tree = MarkdownParser.parse_stream(stream)
      logger.info("File parsing completed successfully")
      return tree
    except Exception as e:
      logger.error(f"Error parsing files: {str(e)}", exc_info=True)
      raise
    finally:
      add_log_context("operation", None)

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
    logger.info(f"Parsing markdown from stdin, concat_stream={is_concat_stream}")
    add_log_context("operation", "parse_stdin")

    try:
      stream = StdinMarkdownStream(is_concat_stream)
      tree = MarkdownParser.parse_stream(stream)
      logger.info("Stdin parsing completed successfully")
      return tree
    except Exception as e:
      logger.error(f"Error parsing stdin: {str(e)}", exc_info=True)
      raise
    finally:
      add_log_context("operation", None)

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
    logger.info(f"Concatenating {len(file_paths)} files")
    add_log_context("operation", "concat_files")

    if not file_paths:
      error_msg = "No files specified for concatenation"
      logger.error(error_msg)
      raise ValueError(error_msg)

    # Use stdout as default output
    output = output_file or sys.stdout
    logger.debug(f"Output destination: {'file' if output_file else 'stdout'}")

    # Process one file at a time
    total_size = 0
    start_time = time.time()

    for file_path in file_paths:
      try:
        logger.debug(f"Processing file: {file_path}")

        # Get file size from stat before opening
        file_stats = os.stat(file_path)
        file_size = file_stats.st_size
        logger.trace(f"File size: {file_size} bytes")
        total_size += file_size

        # Create document separator
        separator = f'<!-- DOC name="{os.path.basename(file_path)}" size_of={file_size} -->'
        output.write(separator + "\n\n")
        logger.trace(f"Wrote document separator for: {file_path}")

        # Process file in chunks to avoid loading it all into memory
        chunk_size = 65536 # 64KB chunks
        chunks_processed = 0
        bytes_processed = 0

        with open(file_path, 'r', encoding='utf-8') as f:
          while True:
            chunk = f.read(chunk_size)
            if not chunk:
              break
            output.write(chunk)
            chunks_processed += 1
            bytes_processed += len(chunk)
            logger.trace(f"Processed chunk {chunks_processed} from {file_path}, size: {len(chunk)} bytes")

        logger.debug(f"Completed file {file_path}: {bytes_processed} bytes in {chunks_processed} chunks")

        # Add newlines between files
        output.write("\n\n")

      except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
      except IOError as e:
        logger.error(f"Error reading {file_path}: {str(e)}", exc_info=True)
        raise IOError(f"Error reading {file_path}: {str(e)}")

    elapsed_time = time.time() - start_time
    logger.info(f"Concatenation completed: {len(file_paths)} files, {total_size} bytes in {elapsed_time:.4f}s")
    add_log_context("operation", None)

  @staticmethod
  def create_cli_parser() -> Any: # argparse.ArgumentParser
    """
        Create the command-line interface parser for source document operations.
        
        Returns:
            Configured argument parser
        """
    import argparse

    logger.debug("Creating CLI parser for source operations")

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

    # Add logging-specific arguments
    parser.add_argument("--log-level", choices=["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"], help="Set logging level")
    parser.add_argument("--log-format", choices=["text", "json"], help="Set log output format")
    parser.add_argument("--log-output", choices=["console", "file", "both"], help="Set log output destination")
    parser.add_argument("--log-file", help="Set log file name (when output is file or both)")

    logger.debug("CLI parser created successfully")
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
    import datetime
    import json

    # Import logger configuration function
    from ._utils.logger import configure_logging, get_logger, set_correlation_id

    # Create a unique correlation ID for this run
    correlation_id = f"kb-source-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    set_correlation_id(correlation_id)

    # Parse command-line arguments first to get logging configuration
    parser = Application.create_cli_parser()
    args = parser.parse_args()

    # Configure logging based on arguments
    configure_logging(level=args.log_level, format_type=args.log_format, output=args.log_output, filename=args.log_file)

    # Get a logger for the application
    logger = get_logger("kb.source.application")
    logger.info(f"KB Source operation starting: {args.action}")
    logger.debug(f"Command line arguments: {vars(args)}")

    try:
      if args.action == "concat":
        logger.info(f"Concatenating {len(args.files)} files")

        # Get output file handle if specified
        output_file = None
        if args.output_file:
          logger.debug(f"Opening output file: {args.output_file}")
          output_file = open(args.output_file, 'w', encoding='utf-8')

        try:
          # Process files incrementally
          Application.concat_files(args.files, output_file)
          logger.info("Concatenation completed successfully")
        finally:
          # Close output file if we opened one
          if output_file:
            logger.debug(f"Closing output file: {args.output_file}")
            output_file.close()

      elif args.action == "validate":
        logger.info(f"Validating {len(args.files)} files")

        # Parse and validate the documents
        tree = MarkdownParser.parse_files(args.files)
        warnings = tree.validate()

        if warnings:
          logger.warning(f"Validation found {len(warnings)} warnings")
          print("Validation warnings:")
          for warning in warnings:
            print(f"- {warning}")
        else:
          logger.info("Validation completed: no issues found")
          print("Documents validated successfully. No issues found.")

      logger.info("KB Source operation completed successfully")

    except (ValueError, FileNotFoundError, IOError) as e:
      logger.error(f"Error: {str(e)}")
      print(f"Error: {str(e)}", file=sys.stderr)
      sys.exit(1)
    except Exception as e:
      logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
      print(f"Error: {str(e)}", file=sys.stderr)
      import traceback
      traceback.print_exc(file=sys.stderr)
      sys.exit(1)

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
  Application.main()
