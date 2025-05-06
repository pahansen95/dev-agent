"""
The Dev Agent's API

Provides a clean interface to the ontology graph and kernel management.
"""

from .ontology import OntologyGraph, Node, Stage
from .interpreter import KernelController, cli_connect, get_client
from jupyter_client import BlockingKernelClient
import subprocess
from typing import Dict, List, Any, Optional, Tuple

class OntologyAPI:
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
    meta: dict | None = None
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
  def add_edge(
    graph: OntologyGraph,
    src: str,
    rel: str,
    dst: str
  ) -> None:
    """Add an edge to the graph."""
    graph.add_edge(src, rel, dst)


class InterpreterAPI:
  """
  A thin wrapper around KernelController providing a consistent interface
  for kernel management operations.
  
  This class bridges the CLI layer with the core kernel management functionality.
  """

  def __init__(self, controller: KernelController):
    self._ctrl = controller

  def create_kernel(
    self,
    name: str,
    extra_args: List[str] | None = None,
    env: Dict[str, str] | None = None,
    replace_existing: bool = False,
  ) -> None:
    """
    Create, but do no start, a new Interpreter session named `name`.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    extra_args : List[str], optional
        Additional arguments for the kernel
    env : Dict[str, str], optional
        Environment variables for the kernel
    replace_existing : bool
        If True, replace existing kernel with this name
    """
    self._ctrl.create_kernel(name, extra_args, env, replace_existing)

  def start_kernel(self, name: str) -> None:
    """
    Start an existing but non-running kernel.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    """
    self._ctrl.start_kernel(name)

  def stop_kernel(self, name: str, missing_ok: bool = False) -> None:
    """
    Shutdown kernel `name`.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    missing_ok : bool
        If True, don't raise error if kernel doesn't exist
    """
    self._ctrl.stop_kernel(name, missing_ok=missing_ok)

  def restart_kernel(self, name: str) -> None:
    """
    Restart an existing kernel.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    """
    self._ctrl.restart_kernel(name)

  def list_kernels(self) -> List[str]:
    """
    Return all known kernel names.
    
    Returns
    -------
    List[str]
        List of kernel identifiers
    """
    return self._ctrl.list_kernels()
    
  def is_kernel_running(self, name: str) -> bool:
    """
    Check if a kernel is running.
    
    Parameters
    ----------
    name : str
        Kernel identifier
        
    Returns
    -------
    bool
        True if kernel is running, False otherwise
    """
    return self._ctrl.is_kernel_running(name)

  def execute(
    self,
    name: str,
    code: str,
    transport: str = "zmq",
    timeout: float = 1.0
  ) -> Tuple[str, Optional[str]]:
    """
    Send `code` to kernel `name` and return execution results.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    code : str
        Python code to execute
    transport : str
        "zmq" for ZeroMQ transport, "http" for HTTP/WebSocket
    timeout : float
        Timeout in seconds for each message
        
    Returns
    -------
    Tuple[str, Optional[str]]
        (stdout, stderr_or_None)
    """
    client = get_client(name, transport=transport)
    msg_id = client.execute(code)
    output: str = ""
    error: Optional[str] = None

    while True:
      msg = client.get_iopub_msg(timeout=timeout)
      t = msg["msg_type"]
      c = msg["content"]
      if t == "stream":
        output += c.get("text", "")
      elif t == "error":
        error = "".join(c.get("traceback", []))
      elif t == "execute_reply":
        break

    return output, error

  def connect_console(self, name: str) -> subprocess.Popen[str]:
    """
    Spawn a live Jupyter console attached to kernel `name`.
    
    Parameters
    ----------
    name : str
        Kernel identifier
        
    Returns
    -------
    subprocess.Popen
        Console process
    """
    return cli_connect(name)

  def get_kernel_info(self, name: str) -> Dict[str, Any]:
    """
    Retrieve metadata for a given kernel.
    
    Parameters
    ----------
    name : str
        Kernel identifier
        
    Returns
    -------
    Dict[str, Any]
        Kernel metadata
    """
    return self._ctrl.read_kernel(name)

  def delete_kernel(self, name: str, missing_ok: bool = False) -> None:
    """
    Delete a kernel: shut it down (if running) and remove its metadata.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    missing_ok : bool
        If True, don't raise error if kernel doesn't exist
    """
    self._ctrl.delete_kernel(name, missing_ok=missing_ok)

# Public module surface
__all__ = [
  'OntologyAPI',
  'InterpreterAPI',
]