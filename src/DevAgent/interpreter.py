"""DevAgent Kernel controller.

This module implements management utilities for IPython/Jupyter kernels so that
other components (CLI or automated agents) can create, start, stop, restart and
connect to a kernel living in the *current working directory*.

All kernel‑specific artefacts (connection files, metadata) are stored beneath
``.kernels/`` in the CWD, making the project directory self‑contained.

Design
------
This module follows a strict separation of concerns:

1. KernelMetadataStore - Pure data manager for on-disk state
   - Manages files/directories without knowledge of kernel semantics
   - Provides raw CRUD operations for metadata

2. KernelLifecycleManager - Pure process manager
   - Manages kernel processes without knowledge of storage details
   - Takes paths and returns process state, but doesn't store it

3. KernelController - Coordinator between storage and processes
   - Only component that understands both metadata and process lifecycle
   - Provides idempotent operations and ensures state consistency

High‑level API
--------------

>>> from DevAgent import interpreter
>>> controller = interpreter.KernelController()
>>> controller.create_kernel("dev")
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

import sys, os, subprocess, signal, json, shutil
from pathlib import Path
from typing import Dict, List, Optional, Any

from jupyter_client import BlockingKernelClient, KernelManager

try:
  # Optional dependency used only for HTTP/WebSocket connections
  from jupyter_kernel_client import KernelClient as HTTPKernelClient  # type: ignore
except ImportError:  # pragma: no cover
  HTTPKernelClient = None  # noqa: N816

# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

# All per‑kernel data are kept here, relative to the project's root.
_KERN_DIR = Path.cwd() / ".devagent"
_KERN_DIR.mkdir(exist_ok=True)


# --------------------------------------------------------------------------- #
# Exceptions                                                                  #
# --------------------------------------------------------------------------- #


class KernelMetaError(RuntimeError):
  """Raised when a kernel's metadata JSON cannot be found or parsed."""


# --------------------------------------------------------------------------- #
# Core CRUD Controller                                                        #
# --------------------------------------------------------------------------- #


class KernelMetadataStore:
  """
  Pure data manager for kernel session metadata.
  
  This class is responsible ONLY for on-disk file operations:
  - Creating and managing directories and files
  - Reading and writing JSON metadata
  - Copying files between locations
  
  It has no knowledge of kernel semantics or processes.
  """

  def __init__(self, base_dir: Path = _KERN_DIR):
    """
    Initialize with a base directory for metadata storage.
    
    Parameters
    ----------
    base_dir : Path
        Directory where metadata will be stored.
        Defaults to .devagent/ in the current working directory.
    """
    self.base_dir = base_dir
    self.base_dir.mkdir(exist_ok=True)
    
  def create_session(self, name: str) -> Dict[str, Any]:
    """
    Create a new session directory with empty metadata.
    
    Parameters
    ----------
    name : str
        Session identifier
        
    Returns
    -------
    Dict[str, Any]
        Empty metadata dictionary
        
    Raises
    ------
    FileExistsError
        If session with this name already exists
    """
    session_dir = self.base_dir / name
    if session_dir.exists():
      raise FileExistsError(f"Session '{name}' already exists")
        
    session_dir.mkdir(parents=True)
    
    # Create empty metadata
    meta = {}
    self._write_json(name, "meta.json", meta)
    return meta
    
  def read_json(self, name: str, filename: str = "meta.json") -> Dict[str, Any]:
    """
    Read a JSON file from a session directory.
    
    Parameters
    ----------
    name : str
        Session identifier
    filename : str
        Name of JSON file to read (default: meta.json)
        
    Returns
    -------
    Dict[str, Any]
        Parsed JSON content
        
    Raises
    ------
    KernelMetaError
        If file doesn't exist or contains invalid JSON
    """
    file_path = self.base_dir / name / filename
    try:
      return json.loads(file_path.read_text())
    except FileNotFoundError as exc:
      raise KernelMetaError(f"File {filename} not found for session '{name}'") from exc
    except json.JSONDecodeError as exc:
      raise KernelMetaError(f"Invalid JSON in {filename} for session '{name}'") from exc
        
  def write_json(self, name: str, data: Dict[str, Any], filename: str = "meta.json") -> None:
    """
    Write data to a JSON file in a session directory.
    
    Parameters
    ----------
    name : str
        Session identifier
    data : Dict[str, Any]
        Data to write
    filename : str
        Name of JSON file to write (default: meta.json)
        
    Raises
    ------
    KernelMetaError
        If session directory doesn't exist
    """
    self._write_json(name, filename, data)
    
  def delete_session(self, name: str, missing_ok: bool = False) -> None:
    """
    Delete a session directory and all its contents.
    
    Parameters
    ----------
    name : str
        Session identifier
    missing_ok : bool
        If True, don't raise error if session doesn't exist
    """
    session_dir = self.base_dir / name
    if session_dir.exists():
      shutil.rmtree(session_dir, ignore_errors=True)
    elif not missing_ok:
      raise KernelMetaError(f"Session '{name}' does not exist")

  def copy_file(self, name: str, src_path: Path, dest_filename: Optional[str] = None) -> Path:
    """
    Copy a file into a session directory.
    
    Parameters
    ----------
    name : str
        Session identifier
    src_path : Path
        Path to source file
    dest_filename : str, optional
        Name to give the file in the session directory (default: same as source)
        
    Returns
    -------
    Path
        Path to the destination file
        
    Raises
    ------
    KernelMetaError
        If session directory doesn't exist
    FileNotFoundError
        If source file doesn't exist
    """
    session_dir = self.base_dir / name
    if not session_dir.exists():
      raise KernelMetaError(f"Session '{name}' does not exist")
      
    if not src_path.exists():
      raise FileNotFoundError(f"Source file {src_path} does not exist")
      
    dest_name = dest_filename or src_path.name
    dest_path = session_dir / dest_name
    
    # Copy the file
    dest_path.write_text(src_path.read_text())
    
    return dest_path
  
  def list_sessions(self) -> List[str]:
    """
    List all session directories.
    
    Returns
    -------
    List[str]
        List of session identifiers
    """
    return [p.name for p in self.base_dir.iterdir() 
            if p.is_dir() and (p / "meta.json").exists()]
    
  def path_exists(self, name: str, filename: str) -> bool:
    """
    Check if a file exists in a session directory.
    
    Parameters
    ----------
    name : str
        Session identifier
    filename : str
        Name of file to check
        
    Returns
    -------
    bool
        True if file exists, False otherwise
    """
    return (self.base_dir / name / filename).exists()
    
  def get_file_path(self, name: str, filename: str) -> Path:
    """
    Get the full path to a file in a session directory.
    
    Parameters
    ----------
    name : str
        Session identifier
    filename : str
        Name of file
        
    Returns
    -------
    Path
        Path to the file
        
    Raises
    ------
    KernelMetaError
        If session doesn't exist
    FileNotFoundError
        If file doesn't exist
    """
    session_dir = self.base_dir / name
    if not session_dir.exists():
      raise KernelMetaError(f"Session '{name}' does not exist")
      
    file_path = session_dir / filename
    if not file_path.exists():
      raise FileNotFoundError(f"File {filename} not found in session '{name}'")
      
    return file_path
    
  def _write_json(self, name: str, filename: str, data: Dict[str, Any]) -> None:
    """Write JSON data to a file."""
    session_dir = self.base_dir / name
    if not session_dir.exists():
      raise KernelMetaError(f"Session '{name}' does not exist")
      
    file_path = session_dir / filename
    file_path.write_text(json.dumps(data, indent=2))


# --------------------------------------------------------------------------- #
# Process Lifecycle Manager                                                   #
# --------------------------------------------------------------------------- #


class KernelLifecycleManager:
  """
  Pure process manager for kernel lifecycle operations.
  
  This class is responsible ONLY for process operations:
  - Starting and stopping kernel processes
  - Monitoring process health
  - Providing client connections to running processes
  
  It has no knowledge of metadata storage or session management.
  """
  
  def __init__(self):
    """Initialize the kernel lifecycle manager."""
    self._managers: Dict[str, KernelManager] = {}
    
  def start_kernel(
    self,
    connection_file: Optional[Path] = None,
    extra_argv: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None
  ) -> tuple[KernelManager, Path]:
    """
    Start a new kernel process.
    
    Parameters
    ----------
    connection_file : Path, optional
        Existing connection file to use (if None, a new one is generated)
    extra_argv : List[str], optional
        Additional arguments to pass to the kernel
    env : Dict[str, str], optional
        Environment variables for the kernel process
        
    Returns
    -------
    tuple[KernelManager, Path]
        The kernel manager and path to the connection file
    """
    # Start new kernel manager
    km = KernelManager(connection_file=str(connection_file) if connection_file else None)
    km_env = dict(os.environ.copy()) if env is None else env
    km.start_kernel(extra_arguments=extra_argv or [], env=km_env)
    
    # Return the manager and connection file path
    return km, Path(km.connection_file)
  
  def connect_to_kernel(self, connection_file: Path) -> KernelManager:
    """
    Connect to an existing kernel using its connection file.
    
    Parameters
    ----------
    connection_file : Path
        Path to the kernel's connection file
        
    Returns
    -------
    KernelManager
        Manager connected to the kernel
        
    Raises
    ------
    FileNotFoundError
        If connection file doesn't exist
    """
    if not connection_file.exists():
      raise FileNotFoundError(f"Connection file {connection_file} not found")
      
    km = KernelManager(connection_file=str(connection_file))
    km.load_connection_file()
    
    # Generate a unique ID for this manager based on the connection file
    # This allows us to track multiple connections to the same kernel
    manager_id = f"conn_{connection_file.stem}"
    self._managers[manager_id] = km
    
    return km
  
  def stop_kernel(self, manager: KernelManager) -> None:
    """
    Stop a kernel process.
    
    Parameters
    ----------
    manager : KernelManager
        Kernel manager to stop
    """
    if manager.is_alive():
      manager.shutdown_kernel(now=True)
      
    # Remove from tracked managers
    to_remove = []
    for manager_id, km in self._managers.items():
      if km is manager:
        to_remove.append(manager_id)
        
    for manager_id in to_remove:
      self._managers.pop(manager_id, None)
  
  def restart_kernel(self, manager: KernelManager) -> None:
    """
    Restart a kernel process.
    
    Parameters
    ----------
    manager : KernelManager
        Kernel manager to restart
    """
    manager.restart_kernel(now=True)
  
  def get_client(self, connection_file: Path) -> BlockingKernelClient:
    """
    Create a client connected to a kernel.
    
    Parameters
    ----------
    connection_file : Path
        Path to the kernel's connection file
        
    Returns
    -------
    BlockingKernelClient
        Client connected to the kernel
        
    Raises
    ------
    FileNotFoundError
        If connection file doesn't exist
    """
    if not connection_file.exists():
      raise FileNotFoundError(f"Connection file {connection_file} not found")
      
    client = BlockingKernelClient(connection_file=str(connection_file))
    client.load_connection_file()
    client.start_channels()
    return client
    
  def is_kernel_alive(self, manager: KernelManager) -> bool:
    """
    Check if a kernel process is alive.
    
    Parameters
    ----------
    manager : KernelManager
        Kernel manager to check
        
    Returns
    -------
    bool
        True if kernel is alive, False otherwise
    """
    return manager.is_alive()
    
  def cleanup(self) -> None:
    """Shutdown all managed kernels."""
    for manager_id, manager in list(self._managers.items()):
      try:
        if manager.is_alive():
          manager.shutdown_kernel(now=True)
      except Exception:  # pragma: no cover
        pass
      
    self._managers.clear()

  # Context manager support
  def __enter__(self) -> "KernelLifecycleManager":
    return self
    
  def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: D401
    self.cleanup()


# --------------------------------------------------------------------------- #
# Compatibility layer for transition                                          #
# --------------------------------------------------------------------------- #


class KernelController:
  """
  Coordinator between metadata storage and process lifecycle.
  
  This class is the only component that understands both metadata and processes:
  - Provides idempotent operations across both domains
  - Ensures state consistency between storage and processes
  - Manages clean transitions between different states
  """
  
  def __init__(self, base_dir: Path = _KERN_DIR):
    """
    Initialize the controller with storage and lifecycle components.
    
    Parameters
    ----------
    base_dir : Path
        Base directory for kernel metadata
    """
    self.metadata_store = KernelMetadataStore(base_dir)
    self.process_manager = KernelLifecycleManager()
    
    # Cache of kernel managers by name for easy lookup
    self._kernel_managers: Dict[str, KernelManager] = {}
    
  # ---------------------- Core State Management ---------------------- #
  
  def _get_manager(self, name: str, require_running: bool = False) -> Optional[KernelManager]:
    """
    Get a kernel manager for a named kernel, optionally requiring it to be running.
    
    This is the central helper method for accessing kernel managers.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    require_running : bool
        If True, raise an error if kernel is not running
        
    Returns
    -------
    Optional[KernelManager]
        Kernel manager, or None if not found/not running
        
    Raises
    ------
    KernelMetaError
        If kernel metadata doesn't exist
    RuntimeError
        If require_running=True and kernel is not running
    """
    # Check the cache first
    km = self._kernel_managers.get(name)
    if km is not None and self.process_manager.is_kernel_alive(km):
      return km
      
    # Cache miss or not running - check metadata
    try:
      meta = self.metadata_store.read_json(name)
      
      # Try to connect using connection file if available
      if "connection_file" in meta:
        try:
          conn_path = self.metadata_store.get_file_path(name, meta["connection_file"])
          km = self.process_manager.connect_to_kernel(conn_path)
          
          # Check if actually running
          if self.process_manager.is_kernel_alive(km):
            self._kernel_managers[name] = km
            return km
            
          # Not running but we connected - clean up
          self.process_manager.stop_kernel(km)
        except FileNotFoundError:
          # Connection file missing
          pass
          
      # Kernel not running
      if require_running:
        raise RuntimeError(f"Kernel '{name}' is not running")
      return None
        
    except KernelMetaError:
      if require_running:
        raise
      return None
  
  def _update_connection_metadata(self, name: str, km: KernelManager) -> None:
    """
    Update metadata with connection info from a kernel manager.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    km : KernelManager
        Kernel manager to get connection info from
    """
    # Read current metadata
    try:
      meta = self.metadata_store.read_json(name)
    except KernelMetaError:
      meta = {}
      
    # Copy connection file to session directory
    conn_file = Path(km.connection_file)
    local_conn = self.metadata_store.copy_file(name, conn_file)
    
    # Update metadata
    meta["connection_file"] = local_conn.name
    meta["updated_at"] = str(os.getenv('SOURCE_DATE_EPOCH') or int(time.time()))
    if "started_at" not in meta:
      meta["started_at"] = meta["updated_at"]
      
    # Save updated metadata
    self.metadata_store.write_json(name, meta)
    
  # ---------------------- Public API Methods ---------------------- #
    
  def create_kernel(
    self,
    name: str,
    extra_argv: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
    replace_existing: bool = False,
    autostart: bool = True,
  ) -> None:
    """
    Create a new kernel session and start the kernel process.
    
    This operation is atomic - either both succeed or both fail.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    extra_argv : List[str], optional
        Additional arguments for the kernel
    env : Dict[str, str], optional
        Environment variables for the kernel
    replace_existing : bool
        If True, replace existing kernel with this name
        
    Raises
    ------
    FileExistsError
        If a kernel with this name already exists and replace_existing=False
    """
    # Handle existing kernels
    if replace_existing and self.metadata_store.path_exists(name, "meta.json"):
      self.delete_kernel(name, missing_ok=True)
    
    # Create metadata directory
    self.metadata_store.create_session(name)
    
    if autostart:
      try:
        # Start the kernel process
        km, _ = self.process_manager.start_kernel(
          extra_argv=extra_argv,
          env=env
        )
        
        # Update metadata and cache
        self._update_connection_metadata(name, km)
        self._kernel_managers[name] = km
        
      except Exception as e:
        # Clean up metadata if process creation fails
        self.metadata_store.delete_session(name, missing_ok=True)
        raise e
    
  def read_kernel(self, name: str) -> Dict[str, Any]:
    """
    Read kernel metadata.
    
    Parameters
    ----------
    name : str
        Kernel identifier
        
    Returns
    -------
    Dict[str, Any]
        Kernel metadata
        
    Raises
    ------
    KernelMetaError
        If kernel doesn't exist
    """
    return self.metadata_store.read_json(name)
    
  def delete_kernel(self, name: str, missing_ok: bool = False) -> None:
    """
    Delete a kernel (stop process and remove metadata).
    
    This is an idempotent operation that ensures both process
    and metadata are cleaned up.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    missing_ok : bool
        If True, don't raise error if kernel doesn't exist
    """
    # First try to stop any running process
    km = self._get_manager(name)
    if km is not None:
      self.process_manager.stop_kernel(km)
      self._kernel_managers.pop(name, None)
    
    # Then delete the metadata
    self.metadata_store.delete_session(name, missing_ok=missing_ok)
    
  def start_kernel(self, name: str) -> None:
    """
    (Re)start a kernel process.
    
    If the kernel is already running, this is a no-op.
    
    Parameters
    ----------
    name : str
        Kernel identifier
        
    Raises
    ------
    KernelMetaError
        If kernel doesn't exist
    """
    # Check if already running
    km = self._get_manager(name)
    if km is not None:
      return  # Already running
      
    # Verify metadata exists
    self.metadata_store.read_json(name)  # Will raise if not exists
    
    # Start new kernel
    km, _ = self.process_manager.start_kernel()
    
    # Update metadata and cache
    self._update_connection_metadata(name, km)
    self._kernel_managers[name] = km
    
  def stop_kernel(self, name: str, *, missing_ok: bool = False) -> None:
    """
    Stop a kernel process.
    
    If the kernel is not running, this is a no-op.
    
    Parameters
    ----------
    name : str
        Kernel identifier
    missing_ok : bool
        If True, don't raise error if kernel doesn't exist
    """
    try:
      # Get manager if running
      km = self._get_manager(name)
      if km is not None:
        self.process_manager.stop_kernel(km)
        self._kernel_managers.pop(name, None)
    except KernelMetaError:
      if not missing_ok:
        raise
    
  def restart_kernel(self, name: str) -> None:
    """
    Restart a kernel process.
    
    If the kernel is not running, it will be started.
    
    Parameters
    ----------
    name : str
        Kernel identifier
        
    Raises
    ------
    KernelMetaError
        If kernel doesn't exist
    """
    # Verify metadata exists
    self.metadata_store.read_json(name)  # Will raise if not exists
    
    # Get current manager if running
    km = self._get_manager(name)
    
    if km is not None:
      # Kernel is running - restart it
      self.process_manager.restart_kernel(km)
    else:
      # Kernel not running - start it
      self.start_kernel(name)
    
  def get_client(self, name: str) -> BlockingKernelClient:
    """
    Get a client connected to a running kernel.
    
    Parameters
    ----------
    name : str
        Kernel identifier
        
    Returns
    -------
    BlockingKernelClient
        Client connected to the kernel
        
    Raises
    ------
    KernelMetaError
        If kernel doesn't exist
    """
    # Get manager, starting kernel if needed
    km = self._get_manager(name)
    if km is None:
      raise ValueError(f'Interpreter {name} Kernel is not running')
      
    # Get connection file path
    conn_path = Path(km.connection_file)
    
    # Get client
    return self.process_manager.get_client(conn_path)
    
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
    return self._get_manager(name) is not None
    
  def list_kernels(self) -> List[str]:
    """
    List all known kernels.
    
    Returns
    -------
    List[str]
        List of kernel identifiers
    """
    return self.metadata_store.list_sessions()
    
  def __enter__(self) -> "KernelController":
    return self
    
  def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: D401
    """Ensure all kernels are cleaned up properly."""
    # Stop all processes first
    for name, km in list(self._kernel_managers.items()):
      try:
        self.process_manager.stop_kernel(km)
      except Exception:  # pragma: no cover
        pass
        
    self._kernel_managers.clear()
    self.process_manager.cleanup()


# --------------------------------------------------------------------------- #
# Helper utilities                                                            #
# --------------------------------------------------------------------------- #

import time  # Add this for the timestamps in KernelController

def cli_connect(name: str) -> subprocess.Popen[str]:
  """
  Spawn jupyter console connected to kernel.
  
  Parameters
  ----------
  name : str
      Kernel identifier
      
  Returns
  -------
  subprocess.Popen
      Console process
  """
  controller = KernelController()
  
  # Ensure kernel is running
  if not controller.is_kernel_running(name):
    controller.start_kernel(name)
  
  # Get connection file info
  meta = controller.read_kernel(name)
  conn_path = controller.metadata_store.get_file_path(name, meta["connection_file"])
  
  # Launch console
  cmd = [sys.executable, "-m", "jupyter", "console", "--existing", str(conn_path)]
  return subprocess.Popen(cmd)


def get_client(name: str, transport: str = "zmq", **kwargs):
  """
  Return a client object connected to kernel.
  
  Parameters
  ----------
  name : str
      Kernel identifier
  transport : str
      "zmq" for ZeroMQ transport, "http" for HTTP/WebSocket
  kwargs
      Additional arguments to pass to client constructor
      
  Returns
  -------
  Union[BlockingKernelClient, HTTPKernelClient]
      Client connected to kernel
  """
  controller = KernelController()
  
  if transport == "zmq":
    return controller.get_client(name)

  if transport == "http":
    if HTTPKernelClient is None:
      raise ImportError(
        "'jupyter_kernel_client' is required for HTTP transport"
      )
    meta = controller.read_kernel(name)
    http_info = meta.get("http", {})
    return HTTPKernelClient(
      server_url=http_info.get("url"),
      token=http_info.get("token"),
      kernel_id=http_info.get("kernel_id"),
      **kwargs,
    )

  raise ValueError("transport must be 'zmq' or 'http'")