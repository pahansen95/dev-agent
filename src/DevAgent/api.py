"""

The Dev Agent's API

"""

from .ontology import OntologyGraph, Node
from .interpreter import KernelController, cli_connect, get_client
from jupyter_client import BlockingKernelClient
import subprocess

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
    graph.add_node(Node(nid, label, kind, meta))

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
  A thin wrapper around KernelController and client helpers,
  with a single Controller instance that you supply.
  """

  def __init__(self, controller: KernelController):
    self._ctrl = controller

  def start_kernel(
    self,
    name: str,
    extra_args: list[str] | None = None,
    env: dict[str, str] | None = None
  ) -> None:
    """Create & start a new Jupyter kernel called `name`."""
    self._ctrl.create_kernel(name, extra_args, env)

  def stop_kernel(self, name: str, missing_ok: bool = False) -> None:
    """Shutdown kernel `name` (no-op if missing_ok and it didn’t exist)."""
    self._ctrl.stop_kernel(name, missing_ok=missing_ok)

  def restart_kernel(self, name: str) -> None:
    """Restart an existing kernel by name."""
    self._ctrl.restart_kernel(name)

  def list_kernels(self) -> list[str]:
    """Return all known kernel names."""
    return self._ctrl.list_kernels()

  def execute(
    self,
    name: str,
    code: str,
    transport: str = "zmq",
    timeout: float = 1.0
  ) -> tuple[str, str | None]:
    """
    Send `code` to kernel `name`, wait up to `timeout` seconds on each message,
    and return (stdout, stderr_traceback_or_None).
    """
    client = get_client(name, transport=transport)
    msg_id = client.execute(code)
    output: str = ""
    error: str | None = None

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
    """Spawn a live Jupyter console attached to kernel `name`."""
    return cli_connect(name)

### The Dev Agent

__all__ = [
  'OntologyAPI',
  'InterpreterAPI',
]