"""
Document-related type definitions for Knowledge Base Generator.

Provides type definitions for document representations, nodes, and tree structures
used throughout the KB Generator.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any

class Document:
    """Represents a document in the content stream."""

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


class Node:
    """Represents a node in the markdown document tree."""

    def __init__(
        self, 
        level: int, 
        title: str, 
        content: str = "", 
        parent: Optional[Node] = None, 
        document: Optional[Document] = None
    ) -> None:
        """
        Initialize a node.
        
        Args:
            level: Header level (1 for #, 2 for ##, etc.)
            title: The node title
            content: The node content
            parent: Optional parent node
            document: Document this node belongs to
        """
        self.level: int = level
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


# Type alias for DocumentNode for backward compatibility 
# (this avoids circular imports by using the same class)
DocumentNode = Node


class Tree:
    """Represents a tree structure of a markdown document."""

    def __init__(self) -> None:
        """Initialize an empty document tree."""
        self.root: Node = Node(0, "ROOT")
        self.current: Node = self.root
        self.document_roots: Dict[str, Node] = {}