"""DevAgent Kernel controller.

This module implements management utilities for IPython/Jupyter kernels so that
other components (CLI or automated agents) can create, start, stop, restart and
connect to a kernel living in the *current working directory*.

All kernel‑specific artefacts (connection files, metadata) are stored beneath
``.kernels/`` in the CWD, making the project directory self‑contained.

High‑level API
--------------

>>> from DevAgent import interpreter
>>> kc = interpreter.KernelController()
>>> kc.create_kernel("dev")
'dev'         # kernel name
>>> interpreter.cli_connect("dev")      # attach interactive console
>>> client = interpreter.get_client("dev")  # programmatic client
>>> client.execute("print('hello')")

Dependencies
------------
* jupyter_client  (pip install jupyter_client)
* ipykernel     (pip install ipykernel)
* Optional: jupyter_kernel_client for HTTP/WebSocket access
"""

from __future__ import annotations

import json
import signal
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from jupyter_client import BlockingKernelClient, KernelManager

try:
  # Optional dependency used only for HTTP/WebSocket connections
  from jupyter_kernel_client import KernelClient as HTTPKernelClient  # type: ignore
except ImportError:  # pragma: no cover
  HTTPKernelClient = None  # noqa: N816

# --------------------------------------------------------------------------- #
# Constants                                   #
# --------------------------------------------------------------------------- #

# All per‑kernel data are kept here, relative to the project’s root.
_KERN_DIR = Path.cwd() / ".kernels"
_KERN_DIR.mkdir(exist_ok=True)


# --------------------------------------------------------------------------- #
# Exceptions                                  #
# --------------------------------------------------------------------------- #


class KernelMetaError(RuntimeError):
  """Raised when a kernel’s metadata JSON cannot be found or parsed."""


# --------------------------------------------------------------------------- #
# Helper utilities                              #
# --------------------------------------------------------------------------- #


def _meta_path(name: str) -> Path:
  """Return the path to the metadata json for *name*."""
  return _KERN_DIR / name / "meta.json"


def _connection_path(name: str) -> Path:
  """Return the connection file path for *name*."""
  meta = KernelController().read_kernel(name)
  return _KERN_DIR / name / meta["connection_file"]


# --------------------------------------------------------------------------- #
# Core controller                               #
# --------------------------------------------------------------------------- #


class KernelController:
  """Manage IPython kernels local to the current project directory."""

  def __init__(self) -> None:
    self._managers: Dict[str, KernelManager] = {}

  # ------------------------------- CRUD ---------------------------------- #

  def create_kernel(
    self,
    name: str,
    extra_argv: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
  ) -> None:
    """Create **and start** a new kernel called *name*.

    A directory ``.kernels/<name>/`` is created.  The kernel's connection
    file is copied into that directory and metadata (PID, file name) is
    stored in ``meta.json``.
    """
    kdir = _KERN_DIR / name
    if kdir.exists():
      raise FileExistsError(f"Kernel '{name}' already exists")

    kdir.mkdir(parents=True)

    km = KernelManager()
    km.start_kernel(extra_arguments=extra_argv or [], env=env)
    conn_file = Path(km.connection_file)

    # Copy the connection file so it is colocated with the metadata
    local_conn = kdir / conn_file.name
    local_conn.write_text(conn_file.read_text())

    meta = {
      "pid": km.kernel.pid if km.is_alive() else None,
      "connection_file": local_conn.name,
    }
    _meta_path(name).write_text(json.dumps(meta, indent=2))
    self._managers[name] = km

  def read_kernel(self, name: str) -> Dict[str, str]:
    """Return persisted metadata for *name*."""
    try:
      return json.loads(_meta_path(name).read_text())
    except FileNotFoundError as exc:
      raise KernelMetaError(f"No metadata for kernel '{name}'") from exc

  def delete_kernel(self, name: str) -> None:
    """Delete kernel metadata directory (does NOT stop the running process)."""
    from shutil import rmtree

    self.stop_kernel(name, missing_ok=True)
    kdir = _KERN_DIR / name
    if kdir.exists():
      rmtree(kdir, ignore_errors=True)

  # --------------------------- Lifecycle ops ---------------------------- #

  def _get_manager(self, name: str) -> KernelManager:
    """Return a live KernelManager for *name*, recreating if necessary."""
    if name in self._managers and self._managers[name].is_alive():
      return self._managers[name]

    meta = self.read_kernel(name)
    conn_path = _KERN_DIR / name / meta["connection_file"]
    km = KernelManager(connection_file=str(conn_path))
    km.load_connection_file()
    self._managers[name] = km
    return km

  def start_kernel(self, name: str) -> None:
    """(Re)start kernel *name* (must already exist)."""
    km = self._get_manager(name)
    if km.is_alive():
      raise RuntimeError(f"Kernel '{name}' already running")
    km.start_kernel()

  def stop_kernel(self, name: str, *, missing_ok: bool = False) -> None:
    """Terminate kernel *name* if it is running."""
    try:
      km = self._get_manager(name)
    except KernelMetaError:
      if missing_ok:
        return
      raise
    if km.is_alive():
      km.shutdown_kernel(now=True)
    self._managers.pop(name, None)

  def restart_kernel(self, name: str) -> None:
    """Restart kernel *name*."""
    km = self._get_manager(name)
    km.restart_kernel(now=True)

  # --------------------------- Client helpers --------------------------- #

  def get_blocking_client(self, name: str) -> BlockingKernelClient:
    """Return a :class:`~jupyter_client.BlockingKernelClient` for *name*."""
    conn_path = _connection_path(name)
    client = BlockingKernelClient(connection_file=str(conn_path))
    client.load_connection_file()
    client.start_channels()
    return client

  def list_kernels(self) -> List[str]:
    """Return a list of available kernel names."""
    return [p.name for p in _KERN_DIR.iterdir() if p.is_dir()]

  # --------------------------- Context mgr ------------------------------ #

  def __enter__(self) -> "KernelController":
    return self

  def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401
    # Ensure all kernels are shut down on exit
    for name in list(self._managers):
      try:
        self.stop_kernel(name, missing_ok=True)
      except Exception:  # pragma: no cover
        pass


# --------------------------------------------------------------------------- #
# Convenience functions for CLI / headless agents               #
# --------------------------------------------------------------------------- #


def cli_connect(name: str) -> subprocess.Popen[str]:
  """Spawn ``jupyter console`` connected to kernel *name*.

  Returns
  -------
  subprocess.Popen
    The running console process.  Call ``.wait()`` to block until the user
    exits.
  """
  conn = _connection_path(name)
  cmd = [sys.executable, "-m", "jupyter", "console", "--existing", str(conn)]
  return subprocess.Popen(cmd)


def get_client(name: str, transport: str = "zmq", **kwargs):
  """Return a client object connected to kernel *name*.

  Parameters
  ----------
  name
    Kernel identifier (directory name under ``.kernels/``).
  transport
    ``"zmq"`` (default) returns a :class:`~jupyter_client.BlockingKernelClient`.
    ``"http"`` returns a :class:`jupyter_kernel_client.KernelClient`
    (requires the *jupyter_kernel_client* extra).
  kwargs
    Passed through to the underlying client constructor.

  """
  if transport == "zmq":
    return KernelController().get_blocking_client(name)

  if transport == "http":
    if HTTPKernelClient is None:
      raise ImportError(
        "'jupyter_kernel_client' is required for HTTP transport"
      )
    meta = KernelController().read_kernel(name)
    http_info = meta.get("http", {})
    return HTTPKernelClient(
      server_url=http_info.get("url"),
      token=http_info.get("token"),
      kernel_id=http_info.get("kernel_id"),
      **kwargs,
    )

  raise ValueError("transport must be 'zmq' or 'http'")