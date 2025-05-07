"""
The Dev Agent's API

Provides a clean interface to the ontology graph and kernel management.
"""
from __future__ import annotations
from .ontology import OntologyGraph, Node, Stage
from .interpreter import (
  KernelController,
  cli_connect,
  get_client,
  JupyterServerManager,
  connect_kernel_websocket,
)
from jupyter_client import BlockingKernelClient
import subprocess
import json
import time
import requests
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Protocol

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

from .interpreter import ServerController
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union

class InterpreterServerAPI(API):

  """Python API for interpreter server operations."""

  def __init__(self, controller: ServerController):
    """
        Initialize with a ServerController instance.
        
        Parameters
        ----------
        controller : ServerController
            The server controller to use for operations
        """
    self.controller = controller

  @classmethod
  def factory(cls, base_dir: Union[str, Path] = None) -> InterpreterServerAPI:
    """
        Create an InterpreterServerAPI instance with a ServerController.
        
        Parameters
        ----------
        base_dir : Union[str, Path], optional
            Base directory for server files, defaults to current working directory
            
        Returns
        -------
        InterpreterAPI
            An initialized InterpreterAPI instance
        """
    if base_dir is None:
      base_dir = os.getcwd()
    controller = ServerController(Path(base_dir))
    return cls(controller)

  def up(self, server_url: Optional[str] = None) -> Dict[str, Any]:
    """
        Start the Jupyter server and return connection information.
        
        Parameters
        ----------
        server_url : Optional[str], optional
            Server URL specification (unix:///path/to/socket.sock or tcp://host:port)
            
        Returns
        -------
        Dict[str, Any]
            Connection information including server URI
            
        Raises
        ------
        RuntimeError
            If server fails to start
        """
    return self.controller.up(server_url)

  def down(self) -> bool:
    """
        Stop the Jupyter server if running.
            
        Returns
        -------
        bool
            True if server was stopped, False if it was not running
        """
    return self.controller.down()

  def status(self) -> Dict[str, Any]:
    """
        Get current Jupyter server status.
            
        Returns
        -------
        Dict[str, Any]
            Status information including:
            - running: bool - Whether server is running
            - connection_info: Dict - Connection details if running
            - pid: int - Process ID if running
            - last_start_time: float - Timestamp of last start
            - last_error: Optional[str] - Last error message
        """
    return self.controller.status()

  def purge(self) -> bool:
    """
        Stop the Jupyter server and remove all state files.
            
        Returns
        -------
        bool
            True if purge was successful
        """
    return self.controller.purge()

# Public module surface
__all__ = [
  "OntologyAPI",
  "InterpreterServerAPI",
]
