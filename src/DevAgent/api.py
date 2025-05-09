"""
The Dev Agent's API

Provides a clean interface to the ontology graph and kernel management.
"""
from __future__ import annotations
from .ontology import OntologyGraph, Node, Stage
from .interpreter.api import InterpreterAPI
from .core import *
import os, atexit, time, pathlib, json
from typing import Dict, List, Any, Optional, Union

class API(Protocol):

  @classmethod
  def factory(cls, *args, **kwds) -> API:
    ...

class OntologyAPI(API):

  """Python API for ontology graph operations."""

  @staticmethod
  def init() -> OntologyGraph:
    """Create a new, empty ontology graph."""
    return OntologyGraph()

  @staticmethod
  def load(data: dict) -> OntologyGraph:
    """Load an ontology graph from a dict."""
    return OntologyGraph.from_dict(data)

  @staticmethod
  def dump(graph: OntologyGraph) -> dict:
    """Serialize the ontology graph to a dict."""
    return graph.to_dict()

  @staticmethod
  def info(graph: OntologyGraph) -> tuple[int, int]:
    """Return (node_count, edge_count) of the graph."""
    return len(graph), len(graph.query())

  @staticmethod
  def add_node(
    graph: OntologyGraph,
    nid: str,
    label: str,
    kind: str = "concept",
    meta: dict | None = None,
  ) -> None:
    """Add a node to the graph."""
    if meta is None:
      meta = {}
    # Handling for kind should now map to proper Stage enums when appropriate
    if hasattr(Stage, kind.upper()):
      stage = getattr(Stage, kind.upper())
      graph.add_node(Node(nid, label, stage, set(), meta))
    else:
      graph.add_node(Node(nid, label, Stage.INTENT, set(), meta))

  @staticmethod
  def add_edge(graph: OntologyGraph, src: str, rel: str, dst: str) -> None:
    """Add an edge to the graph."""
    graph.add_edge(src, rel, dst)

# Public module surface
__all__ = [
  "OntologyAPI",
  "InterpreterAPI",
]