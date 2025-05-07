"""
The Dev Agent's API

Provides a clean interface to the ontology graph and kernel management.
"""

from .ontology import OntologyGraph, Node, Stage
from .interpreter import KernelController, cli_connect, get_client, JupyterServerManager, connect_kernel_websocket
from jupyter_client import BlockingKernelClient
import subprocess
import json
import time
import requests
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

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
  
  This class bridges the CLI layer with the core kernel management functionality
  and provides additional support for Jupyter Server operations.
  """

  def __init__(self, controller: Optional[KernelController] = None):
    """
    Initialize the API with an optional controller.
    
    Parameters
    ----------
    controller : Optional[KernelController]
      Kernel controller instance or None to create a new one
    """
    self._ctrl = controller or KernelController()
    
    # Create server manager
    self._server_manager = JupyterServerManager()
    
    # Directory for kernel state persistence
    self._kernel_state_dir = self._ctrl.metadata_store.base_dir / "kernel_state"
    self._kernel_state_dir.mkdir(exist_ok=True, parents=True)
  
  # Server management methods
  
  def server_up(self, server_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Ensure the Jupyter Server is running, starting it if needed.
    
    After starting the server, automatically restore kernels that
    were running previously.
    
    Parameters
    ----------
    server_url : Optional[str]
      Server URL specification (unix:///path/to/socket.sock or tcp://host:port)
      If None, defaults to Unix socket in state directory
      
    Returns
    -------
    Dict[str, Any]
      Connection information
    """
    connection_info = self._server_manager.up(server_url)
    
    # Restore previously running kernels
    self._restore_kernels()
    
    return connection_info
  
  def server_down(self) -> bool:
    """
    Stop the Jupyter Server if running.
    
    Returns
    -------
    bool
      True if server was running and was stopped
    """
    return self._server_manager.down()
  
  def server_purge(self) -> bool:
    """
    Stop the server and remove all state.
    
    Returns
    -------
    bool
      True if purge was successful
    """
    return self._server_manager.purge()
  
  # Kernel state persistence methods
  
  def _save_kernel_state(self, name: str, kernel_id: str, kernel_spec: str = "python3", 
              env: Optional[Dict[str, str]] = None, running: bool = True) -> None:
    """
    Save kernel state for persistence across server restarts.
    
    Parameters
    ----------
    name : str
      Kernel name
    kernel_id : str
      Jupyter kernel ID
    kernel_spec : str
      Kernel specification name
    env : Optional[Dict[str, str]]
      Environment variables
    running : bool
      Whether the kernel is currently running
    """
    state_file = self._kernel_state_dir / f"{name}.json"
    
    state = {
      "name": name,
      "kernel_id": kernel_id,
      "kernel_spec": kernel_spec,
      "running": running
    }
    
    if env:
      state["env"] = env
    
    with open(state_file, "w") as f:
      json.dump(state, f)
  
  def _get_kernel_state(self, name: str) -> Optional[Dict[str, Any]]:
    """
    Get saved kernel state.
    
    Parameters
    ----------
    name : str
      Kernel name
      
    Returns
    -------
    Optional[Dict[str, Any]]
      Kernel state or None if not found
    """
    state_file = self._kernel_state_dir / f"{name}.json"
    
    if not state_file.exists():
      return None
    
    try:
      with open(state_file, "r") as f:
        return json.load(f)
    except Exception as e:
      from . import logger
      logger.warning(f"Error reading kernel state for {name}: {e}")
      return None
  
  def _update_kernel_state(self, name: str, **kwargs) -> None:
    """
    Update kernel state with new values.
    
    Parameters
    ----------
    name : str
      Kernel name
    **kwargs
      Values to update
    """
    state = self._get_kernel_state(name)
    
    if state is None:
      return
    
    # Update state with new values
    state.update(kwargs)
    
    # Write updated state
    state_file = self._kernel_state_dir / f"{name}.json"
    with open(state_file, "w") as f:
      json.dump(state, f)
  
  def _delete_kernel_state(self, name: str) -> None:
    """
    Delete kernel state file.
    
    Parameters
    ----------
    name : str
      Kernel name
    """
    state_file = self._kernel_state_dir / f"{name}.json"
    state_file.unlink(missing_ok=True)
  
  def _get_running_kernels(self) -> List[Dict[str, Any]]:
    """
    Get list of kernels marked as running.
    
    Returns
    -------
    List[Dict[str, Any]]
      List of kernel states
    """
    running_kernels = []
    
    for state_file in self._kernel_state_dir.glob("*.json"):
      try:
        with open(state_file, "r") as f:
          state = json.load(f)
        
        if state.get("running", False):
          running_kernels.append(state)
      except Exception as e:
        from . import logger
        logger.warning(f"Error reading kernel state from {state_file}: {e}")
    
    return running_kernels
  
  def _restore_kernels(self) -> None:
    """
    Restore previously running kernels after server restart.
    """
    if not self._server_manager.is_server_running():
      from . import logger
      logger.warning("Cannot restore kernels: Jupyter Server not running")
      return
    
    # Get connection info
    with open(self._server_manager.connection_file, "r") as f:
      connection_info = json.load(f)
    
    # Get base URL and headers for API requests
    if connection_info.get("use_unix_socket"):
      # Unix socket connection requires special handling for requests
      import urllib.parse
      socket_path = connection_info.get("socket_path")
      encoded_path = urllib.parse.quote_plus(socket_path)
      base_url = f"http+unix://{encoded_path}"
    else:
      # TCP connection
      host = connection_info.get("host", "127.0.0.1")
      port = connection_info.get("port")
      base_url = f"http://{host}:{port}"
    
    headers = {"Authorization": f"Token {connection_info.get('token')}"}
    
    # Restore each running kernel
    for kernel in self._get_running_kernels():
      name = kernel.get("name")
      kernel_spec = kernel.get("kernel_spec", "python3")
      env = kernel.get("env")
      
      from . import logger
      logger.info(f"Restoring kernel: {name}")
      
      # Create kernel via server API
      data = {"name": kernel_spec}
      if env:
        data["env"] = env
      
      try:
        response = requests.post(
          f"{base_url}/api/kernels",
          headers=headers,
          json=data
        )
        
        if response.status_code != 201:
          logger.error(f"Failed to restore kernel {name}: {response.text}")
          continue
        
        # Get new kernel ID
        kernel_id = response.json().get("id")
        
        # Update kernel state with new ID
        self._update_kernel_state(name, kernel_id=kernel_id, running=True)
        
        logger.info(f"Kernel {name} restored with ID {kernel_id}")
      
      except Exception as e:
        logger.error(f"Error restoring kernel {name}: {e}")

  # Extend existing methods and add server-based kernel management

  def create_kernel(
    self,
    name: str,
    kernel_spec: str = "python3",
    extra_args: List[str] | None = None,
    env: Dict[str, str] | None = None,
    replace_existing: bool = False,
  ) -> str:
    """
    Create a new kernel via Jupyter Server (if running) or directly.
    
    Parameters
    ----------
    name : str
      Kernel identifier
    kernel_spec : str
      Name of the kernel spec (default: python3)
    extra_args : List[str], optional
      Additional arguments for the kernel
    env : Dict[str, str], optional
      Environment variables for the kernel
    replace_existing : bool
      If True, replace existing kernel with this name
      
    Returns
    -------
    str
      Kernel ID
    """
    # Check if server is running
    if self._server_manager.is_server_running():
      # Use server for kernel management
      
      # Handle existing kernel
      state = self._get_kernel_state(name)
      if state is not None:
        if replace_existing:
          self.delete_kernel(name)
        else:
          raise ValueError(f"Kernel '{name}' already exists")
      
      # Get connection info
      with open(self._server_manager.connection_file, "r") as f:
        connection_info = json.load(f)
      
      # Setup API request
      if connection_info.get("use_unix_socket"):
        import urllib.parse
        socket_path = connection_info.get("socket_path")
        encoded_path = urllib.parse.quote_plus(socket_path)
        base_url = f"http+unix://{encoded_path}"
      else:
        host = connection_info.get("host", "127.0.0.1")
        port = connection_info.get("port")
        base_url = f"http://{host}:{port}"
      
      headers = {"Authorization": f"Token {connection_info.get('token')}"}
      
      # Create kernel via API
      data = {"name": kernel_spec}
      if env:
        data["env"] = env
      
      response = requests.post(
        f"{base_url}/api/kernels",
        headers=headers,
        json=data
      )
      
      if response.status_code != 201:
        raise RuntimeError(f"Failed to create kernel: {response.text}")
      
      # Get kernel ID
      kernel_id = response.json().get("id")
      
      # Save kernel state for persistence
      self._save_kernel_state(name, kernel_id, kernel_spec, env)
      
      return kernel_id
    else:
      # Fall back to direct kernel management
      self._ctrl.create_kernel(name, extra_args, env, replace_existing)
      self._ctrl.start_kernel(name)
      # Get info for state tracking
      kernel_info = self._ctrl.get_kernel_info(name)
      # Save minimal state
      self._save_kernel_state(name, name, kernel_spec, env)
      return name

  def start_kernel(self, name: str) -> None:
    """
    Start an existing kernel or create if it doesn't exist.
    
    Parameters
    ----------
    name : str
      Kernel identifier
    """
    # Check if kernel already exists
    state = self._get_kernel_state(name)
    
    if state is None:
      # Create new kernel
      self.create_kernel(name)
      return
    
    # Check if server is running
    if self._server_manager.is_server_running():
      # Get connection info
      with open(self._server_manager.connection_file, "r") as f:
        connection_info = json.load(f)
      
      # Setup API request
      if connection_info.get("use_unix_socket"):
        import urllib.parse
        socket_path = connection_info.get("socket_path")
        encoded_path = urllib.parse.quote_plus(socket_path)
        base_url = f"http+unix://{encoded_path}"
      else:
        host = connection_info.get("host", "127.0.0.1")
        port = connection_info.get("port")
        base_url = f"http://{host}:{port}"
      
      headers = {"Authorization": f"Token {connection_info.get('token')}"}
      
      # Check if kernel exists on server
      kernel_id = state.get("kernel_id")
      response = requests.get(
        f"{base_url}/api/kernels/{kernel_id}",
        headers=headers
      )
      
      if response.status_code != 200:
        # Kernel doesn't exist on server, create new one
        self.create_kernel(
          name, 
          kernel_spec=state.get("kernel_spec", "python3"),
          env=state.get("env"),
          replace_existing=True
        )
      else:
        # Mark kernel as running
        self._update_kernel_state(name, running=True)
    else:
      # Fall back to direct kernel management
      self._ctrl.start_kernel(name)
      self._update_kernel_state(name, running=True)

  def stop_kernel(self, name: str, missing_ok: bool = False) -> None:
    """
    Stop a kernel.
    
    Parameters
    ----------
    name : str
      Kernel identifier
    missing_ok : bool
      If True, don't raise error if kernel doesn't exist
    """
    # Check if kernel exists
    state = self._get_kernel_state(name)
    if state is None:
      if missing_ok:
        return
      raise ValueError(f"Kernel '{name}' not found")
    
    # Check if server is running
    if self._server_manager.is_server_running():
      # Get connection info
      with open(self._server_manager.connection_file, "r") as f:
        connection_info = json.load(f)
      
      # Setup API request
      if connection_info.get("use_unix_socket"):
        import urllib.parse
        socket_path = connection_info.get("socket_path")
        encoded_path = urllib.parse.quote_plus(socket_path)
        base_url = f"http+unix://{encoded_path}"
      else:
        host = connection_info.get("host", "127.0.0.1")
        port = connection_info.get("port")
        base_url = f"http://{host}:{port}"
      
      headers = {"Authorization": f"Token {connection_info.get('token')}"}
      
      # Delete kernel via API
      kernel_id = state.get("kernel_id")
      response = requests.delete(
        f"{base_url}/api/kernels/{kernel_id}",
        headers=headers
      )
      
      # Update state regardless of API response
      self._update_kernel_state(name, running=False)
      
      if response.status_code not in (204, 404) and not missing_ok:
        raise RuntimeError(f"Failed to stop kernel: {response.text}")
    else:
      # Fall back to direct kernel management
      try:
        self._ctrl.stop_kernel(name, missing_ok=missing_ok)
      finally:
        self._update_kernel_state(name, running=False)

  def delete_kernel(self, name: str, missing_ok: bool = False) -> None:
    """
    Delete a kernel: stop it and remove its metadata.
    
    Parameters
    ----------
    name : str
      Kernel identifier
    missing_ok : bool
      If True, don't raise error if kernel doesn't exist
    """
    # Stop kernel
    try:
      self.stop_kernel(name, missing_ok=missing_ok)
    except Exception as e:
      if not missing_ok:
        raise
    
    # Delete state
    self._delete_kernel_state(name)
    
    # Clean up direct kernel if needed
    try:
      self._ctrl.delete_kernel(name, missing_ok=True)
    except:
      pass

  def restart_kernel(self, name: str) -> None:
    """
    Restart a kernel.
    
    Parameters
    ----------
    name : str
      Kernel identifier
    """
    # Check if kernel exists
    state = self._get_kernel_state(name)
    if state is None:
      raise ValueError(f"Kernel '{name}' not found")
    
    # Check if server is running
    if self._server_manager.is_server_running():
      # Get connection info
      with open(self._server_manager.connection_file, "r") as f:
        connection_info = json.load(f)
      
      # Setup API request
      if connection_info.get("use_unix_socket"):
        import urllib.parse
        socket_path = connection_info.get("socket_path")
        encoded_path = urllib.parse.quote_plus(socket_path)
        base_url = f"http+unix://{encoded_path}"
      else:
        host = connection_info.get("host", "127.0.0.1")
        port = connection_info.get("port")
        base_url = f"http://{host}:{port}"
      
      headers = {"Authorization": f"Token {connection_info.get('token')}"}
      
      # Restart kernel via API
      kernel_id = state.get("kernel_id")
      response = requests.post(
        f"{base_url}/api/kernels/{kernel_id}/restart",
        headers=headers
      )
      
      if response.status_code != 200:
        # If restart fails, try creating a new kernel
        self.delete_kernel(name, missing_ok=True)
        self.create_kernel(
          name, 
          kernel_spec=state.get("kernel_spec", "python3"),
          env=state.get("env")
        )
    else:
      # Fall back to direct kernel management
      self._ctrl.restart_kernel(name)
      self._update_kernel_state(name, running=True)

  def execute(
    self,
    name: str,
    code: str,
    timeout: float = 30.0
  ) -> Tuple[str, Optional[str]]:
    """
    Execute code on a kernel and return results.
    
    Parameters
    ----------
    name : str
      Kernel identifier
    code : str
      Python code to execute
    timeout : float
      Timeout in seconds
      
    Returns
    -------
    Tuple[str, Optional[str]]
      (stdout, stderr or None)
    """
    # Check if kernel exists
    state = self._get_kernel_state(name)
    if state is None:
      raise ValueError(f"Kernel '{name}' not found")
    
    # Check if server is running
    if self._server_manager.is_server_running():
      # Ensure kernel is running
      if not state.get("running", False):
        self.start_kernel(name)
        # Re-read state to get updated kernel_id
        state = self._get_kernel_state(name)
      
      # Get connection info
      with open(self._server_manager.connection_file, "r") as f:
        connection_info = json.load(f)
      
      # Connect to kernel
      kernel_id = state.get("kernel_id")
      
      try:
        conn = connect_kernel_websocket(kernel_id, connection_info)
      except Exception as e:
        # If connection fails, try restarting kernel
        from . import logger
        logger.warning(f"Error connecting to kernel: {e}")
        self.restart_kernel(name)
        state = self._get_kernel_state(name)
        kernel_id = state.get("kernel_id")
        conn = connect_kernel_websocket(kernel_id, connection_info)
      
      try:
        # Execute code
        msg_id = conn.execute(code)
        
        # Collect outputs
        output = []
        error = None
        
        # Wait for results
        start_time = time.time()
        
        while time.time() - start_time < timeout:
          try:
            msg = conn.get_iopub_msg(timeout=0.1)
            
            # Parse message
            msg_type = msg.get("msg_type", "")
            parent_id = msg.get("parent_header", {}).get("msg_id", "")
            
            # Only process messages related to our execution request
            if parent_id != msg_id:
              continue
            
            if msg_type == "stream":
              content = msg.get("content", {})
              text = content.get("text", "")
              output.append(text)
            
            elif msg_type == "error":
              content = msg.get("content", {})
              traceback = content.get("traceback", [])
              error = "\n".join(traceback)
            
            elif msg_type == "execute_reply":
              # Execution completed
              break
          
          except Exception:
            # Ignore empty queue exceptions
            pass
        
        return "".join(output), error
      
      finally:
        # Cleanup
        conn.stop()
    else:
      # Fall back to direct execution
      return self._ctrl.execute(name, code)

  def connect_console(self, name: str) -> subprocess.Popen:
    """
    Spawn a live Jupyter console attached to a kernel.
    
    Parameters
    ----------
    name : str
      Kernel identifier
      
    Returns
    -------
    subprocess.Popen
      Console process
    """
    # Check if kernel exists
    state = self._get_kernel_state(name)
    if state is None:
      raise ValueError(f"Kernel '{name}' not found")
    
    # Check if server is running
    if self._server_manager.is_server_running():
      # Ensure kernel is running
      if not state.get("running", False):
        self.start_kernel(name)
        # Re-read state to get updated kernel_id
        state = self._get_kernel_state(name)
      
      # Get kernel ID
      kernel_id = state.get("kernel_id")
      
      # Get connection info
      with open(self._server_manager.connection_file, "r") as f:
        connection_info = json.load(f)
      
      # Create temporary gateway config file
      gateway_file = self._server_manager.jupyter_dir / f"console-gateway-{name}.json"
      
      gateway_config = {
        "kernel_id": kernel_id,
      }
      
      if connection_info.get("use_unix_socket"):
        # Unix socket connection
        socket_path = connection_info.get("socket_path")
        gateway_config.update({
          "url": f"http+unix://{socket_path}",
          "socket": True
        })
      else:
        # TCP connection
        host = connection_info.get("host", "127.0.0.1")
        port = connection_info.get("port")
        gateway_config.update({
          "url": f"http://{host}:{port}",
        })
      
      gateway_config["token"] = connection_info["token"]
      
      with open(gateway_file, "w") as f:
        json.dump(gateway_config, f)
      
      # Launch console
      cmd = [
        sys.executable, "-m", "jupyter", "console",
        "--existing", str(gateway_file)
      ]
      
      return subprocess.Popen(cmd)
    else:
      # Fall back to direct connection
      return cli_connect(name)

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
      True if kernel is running
    """
    # Check if kernel exists
    state = self._get_kernel_state(name)
    if state is None:
      return False
    
    # Check if server is running
    if self._server_manager.is_server_running():
      # Get kernel ID
      kernel_id = state.get("kernel_id")
      
      # Get connection info
      with open(self._server_manager.connection_file, "r") as f:
        connection_info = json.load(f)
      
      # Setup API request
      if connection_info.get("use_unix_socket"):
        import urllib.parse
        socket_path = connection_info.get("socket_path")
        encoded_path = urllib.parse.quote_plus(socket_path)
        base_url = f"http+unix://{encoded_path}"
      else:
        host = connection_info.get("host", "127.0.0.1")
        port = connection_info.get("port")
        base_url = f"http://{host}:{port}"
      
      headers = {"Authorization": f"Token {connection_info.get('token')}"}
      
      # Check kernel status via API
      try:
        response = requests.get(
          f"{base_url}/api/kernels/{kernel_id}",
          headers=headers
        )
        return response.status_code == 200
      except Exception:
        return False
    else:
      # Fall back to direct check
      return self._ctrl.is_kernel_running(name)

  def list_kernels(self) -> List[Dict[str, Any]]:
    """
    List all known kernels.
    
    Returns
    -------
    List[Dict[str, Any]]
      List of kernel information
    """
    kernels = []
    
    # Get all kernel states
    for state_file in self._kernel_state_dir.glob("*.json"):
      try:
        with open(state_file, "r") as f:
          state = json.load(f)
        
        # Check if kernel is running
        is_running = False
        if self._server_manager.is_server_running():
          is_running = self.is_kernel_running(state.get("name"))
        elif self._ctrl.is_kernel_running(state.get("name")):
          is_running = True
        
        # Update running state
        state["running"] = is_running
        
        kernels.append(state)
      except Exception as e:
        from . import logger
        logger.warning(f"Error reading kernel state from {state_file}: {e}")
    
    return kernels
  
  def server_status(self) -> Dict[str, Any]:
    """
    Get current server status.
    
    Returns
    -------
    Dict[str, Any]
      Status information including whether server is running
    """
    is_running = self._server_manager.is_server_running()
    status = {"running": is_running}
    
    if is_running and self._server_manager.connection_file.exists():
      try:
        with open(self._server_manager.connection_file, "r") as f:
          connection_info = json.load(f)
        status["connection_info"] = connection_info
      except Exception as e:
        status["error"] = str(e)
    
    return status
    
  def launch_lab(self) -> None:
    """
    Launch Jupyter Lab interface in the web browser.
    
    This allows interactive access to all kernels.
    """
    # Ensure server is running
    if not self._server_manager.is_server_running():
      self.server_up()
    
    # Get connection info
    with open(self._server_manager.connection_file, "r") as f:
      connection_info = json.load(f)
    
    # Determine URL
    if connection_info.get("use_unix_socket"):
      # Unix socket - cannot directly open browser
      raise NotImplementedError(
        "JupyterLab launch with Unix sockets requires additional configuration"
      )
    else:
      # TCP connection
      host = connection_info.get("host", "127.0.0.1")
      port = connection_info.get("port")
      token = connection_info.get("token")
      url = f"http://{host}:{port}/lab?token={token}"
    
    # Open in browser
    import webbrowser
    webbrowser.open(url)
    print(f"Opened JupyterLab at {url}")

  # Keep existing methods for backward compatibility
  
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

  def get_client(self, name: str) -> BlockingKernelClient:
    """Get a client connected to a kernel."""
    return self._ctrl.get_client(name)

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

# Public module surface
__all__ = [
  'OntologyAPI',
  'InterpreterAPI',
]