"""
DevAgent Interpreter Server Module

This module provides server management capabilities for the DevAgent Interpreter system.
It handles the complete lifecycle of Jupyter server processes, including starting,
stopping, configuration, and monitoring server instances.

The server module acts as a foundation layer for the Interpreter architecture,
creating stable computational environments where kernels can be executed. It provides
isolation between the DevAgent runtime and execution environments through protocol-agnostic
connection management.

Key Components
-------------
- ServerController: Central component managing Jupyter server processes
- Connection management: Support for both Unix sockets and TCP connections
- Configuration management: Secure handling of tokens and server settings
- Process lifecycle: Clean startup/shutdown with proper signal handling

Security Aspects
---------------
- Token authentication: Secure token generation and management
- File permissions: Proper permission controls for sensitive files
- Process isolation: Servers run in independent process groups
- Connection validation: Reliable connection testing and validation

Usage Examples
-------------
Basic server startup:

    controller = ServerController(base_dir="/path/to/workspace")
    connection_info = controller.up()

Custom server configuration:

    # TCP server on specific port
    connection_info = controller.up("tcp://localhost:8888")

    # Unix socket at custom path
    connection_info = controller.up("unix:///path/to/custom.sock")

This module is designed to be used as part of the broader DevAgent Interpreter system,
but can also be used independently when only server management is needed.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import subprocess
import json
import time
import os
import signal
import logging
import tempfile
import requests
import socket
import secrets
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def _parse_uri(uri: str) -> Tuple[str, Union[Path, Tuple[str, int]]]:
  """
    Parse a server URI into protocol and address components.

    Parameters
    ----------
    uri : str
        URI in the format 'unix:///path/to/socket.sock' or 'tcp://host:port'

    Returns
    -------
    Tuple[str, Union[Path, Tuple[str, int]]]
        (protocol, address) where:
        - protocol is 'unix' or 'tcp'
        - address is either a Path object (for unix) or a (host, port) tuple (for tcp)

    Raises
    ------
    AssertionError
        If the URI has an unsupported protocol
    """
  parsed = urlparse(uri)
  protocol = parsed.scheme
  assert protocol in {"unix", "tcp"}

  if protocol == "unix":
    address = Path(parsed.path)
  else: # tcp
    if ":" in parsed.netloc:
      host, port_str = parsed.netloc.split(":")
      address = (host, int(port_str))
    else:
      host = parsed.netloc or "localhost"
      address = (host, 8888)

  return protocol, address

class ServerController:

  """
    Manages the lifecycle of a Jupyter Server process.

    This component is responsible for starting, stopping, and monitoring a Jupyter Server
    process. It handles configuration, process management, and provides status information.
    It has no knowledge of kernels or how they're used - it simply ensures a server is
    available when needed.
    """

  def __init__(self, base_dir: Union[str, Path]):
    """
        Initialize the server controller.

        Parameters
        ----------
        base_dir : Union[str, Path]
            Base directory for server-related files
        """
    # Convert to Path object if string
    self.base_dir = Path(base_dir)

    # Ensure base directory exists
    if not self.base_dir.exists():
      raise ValueError(f"Base directory does not exist: {self.base_dir}")

    # Create hidden server state directory
    self.state_dir = self.base_dir / ".server"
    self.state_dir.mkdir(exist_ok=True)

    # Define paths for server files
    self.state_file = self.state_dir / "state.json"
    self.log_file = self.state_dir / "jupyter_server.log"
    self.socket_path = self.state_dir / "jupyter.sock"
    self.config_dir = self.state_dir / "config"
    self.config_dir.mkdir(exist_ok=True)
    self.config_file = self.config_dir / "jupyter_server_config.py"
    self.token_file = self.config_dir / "token"
    self.cookie_secret_file = self.config_dir / "cookie_secret"

    # Initialize state
    self._initialize_state()

  def up(self, server_url: Optional[str] = None) -> Dict[str, Any]:
    """
      Ensure Jupyter Server is running, starting it if needed.

      This operation is idempotent - if the server is already running,
      it will return the connection information.

      Parameters
      ----------
      server_url : Optional[str]
          Server URL specification (unix:///path/to/socket.sock or tcp://host:port)
          If None, defaults to Unix socket in state directory

      Returns
      -------
      Dict[str, Any]
          Connection information including:
          - uri: str - Complete server URI

      Raises
      ------
      RuntimeError
          If server fails to start
    """
    # Check if server is already running
    if self.is_running():
      logger.info("Server already running")
      return self._get_connection_info()

    # If no URL provided, use default socket path
    if server_url is None:
      server_url = f"unix://{self.socket_path}"

    # Parse server URL
    protocol, address = _parse_uri(server_url)

    # Create configuration files
    self._create_config_files(protocol, address)

    # Build command with proper arguments
    cmd = ["jupyter", "server"]
    cmd.extend(["--config", str(self.config_file)])

    # Start the server process
    logger.info(f"Starting Jupyter server with command: {' '.join(cmd)}")

    with open(self.log_file, "wb") as log_file:
      process = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True, # Create new process group
      )

    # Create connection info
    connection_info = {"uri": server_url}

    # Save initial state
    self._save_state(
      running=True,
      pid=process.pid,
      last_start_time=time.time(),
      connection_info=connection_info,
    )

    # Wait for server to be ready
    self._wait_for_server_ready(server_url)

    return connection_info

  def down(self) -> bool:
    """
      Stop the Jupyter Server if it's running.

      This operation is idempotent - if the server is not running,
      it will simply return False.

      Returns
      -------
      bool
          True if server was stopped, False if it was not running
    """
    # Check if server is running
    if not self.is_running():
      logger.info("Server is not running")
      return False

    # Get server state
    state = self._load_state()
    pid = state.get("pid")

    if not pid:
      logger.warning("Server marked as running but no PID found")
      self._save_state(running=False)
      return False

    # Try graceful shutdown first
    logger.info(f"Stopping Jupyter server (PID: {pid})")

    try:
      # Try stopping using SIGTERM
      os.kill(pid, signal.SIGTERM)

      # Wait for process to terminate
      shutdown_timeout = 10 # seconds
      shutdown_start = time.time()

      while time.time() - shutdown_start < shutdown_timeout:
        try:
          # Check if process exists by sending signal 0
          os.kill(pid, 0)
          # Process still exists, wait a bit
          time.sleep(0.5)
        except OSError:
          # Process no longer exists
          logger.info(f"Server stopped gracefully")
          break
      else:
        # Timeout expired, force kill
        logger.warning(f"Server didn't terminate gracefully, forcing kill")
        try:
          os.kill(pid, signal.SIGKILL)
        except OSError:
          pass # Process might be gone already

    except OSError as e:
      logger.warning(f"Error stopping server: {e}")
      # Process might be gone already

    # Update state
    self._save_state(running=False, pid=None, connection_info=None)

    return True

  def purge(self) -> bool:
    """
      Stop the server and remove all state.

      This operation is destructive and will remove all server-related files.

      Returns
      -------
      bool
          True if purge was successful
    """
    # Stop the server if running
    if self.is_running():
      self.down()

    # Remove server files
    success = all(
      [
        self._safe_delete(self.log_file),
        self._safe_delete(self.state_file),
        self._safe_delete(self.socket_path),
        self._safe_delete(self.token_file),
        self._safe_delete(self.cookie_secret_file),
        self._safe_delete(self.config_file),
      ])

    # Re-initialize state
    self._initialize_state()

    return success

  def status(self) -> Dict[str, Any]:
    """
      Get current server status.

      Returns
      -------
      Dict[str, Any]
          Status information including:
          - running: bool - Whether server is running
          - connection_info: Dict - Connection details if running
          - pid: int - Process ID if running
    """
    # Refresh running state
    is_running = self.is_running()

    # Get current state
    state = self._load_state()

    # Prepare status report
    status = {
      "running": is_running,
      "pid": state.get("pid") if is_running else None,
      "connection_info": state.get("connection_info") if is_running else None,
      "last_start_time": state.get("last_start_time"),
      "last_error": state.get("last_error"),
    }

    return status

  def is_running(self) -> bool:
    """
      Check if the Jupyter Server is running.

      Returns
      -------
      bool
          True if server is running and responsive
    """
    # Check state file first
    state = self._load_state()
    if not state.get("running", False):
      return False

    # Verify process exists using helper method
    if not self._is_process_running():
      self._save_state(running=False, pid=None)
      return False

    # Get connection info
    connection_info = state.get("connection_info", {})
    if not connection_info:
      return False

    # Get the URI
    uri = connection_info.get("uri")
    if not uri:
      return False

    # Parse the URI
    protocol, address = _parse_uri(uri)

    # Test socket connection
    return self._test_connection(protocol, address)

  # Private methods

  def _initialize_state(self) -> None:
    """
      Initialize or load the server state file.

      Creates a default state file if one doesn't exist.
    """
    if not self.state_file.exists():
      # Create default state
      default_state = {
        "running": False,
        "pid": None,
        "connection_info": None,
        "last_start_time": None,
        "last_error": None,
      }

      # Write state to file
      with open(self.state_file, "w") as f:
        json.dump(default_state, f, indent=2)

    # Read current state
    self._load_state()

  def _load_state(self) -> Dict[str, Any]:
    """
      Load server state from state file.

      Returns
      -------
      Dict[str, Any]
          The current server state
    """
    try:
      with open(self.state_file, "r") as f:
        state = json.load(f)
      self._state = state
      return state
    except (json.JSONDecodeError, FileNotFoundError) as e:
      logger.warning(f"Error loading state file: {e}")
      # Reinitialize state file
      self._initialize_state()
      return self._state

  def _save_state(self, **updates) -> None:
    """
      Update and save server state.

      Parameters
      ----------
      **updates
          Key-value pairs to update in the state
    """
    # Update state
    state = self._load_state()
    state.update(updates)
    self._state = state

    # Write to temporary file first (atomic update)
    temp_file = self.state_file.with_suffix(".tmp")
    with open(temp_file, "w") as f:
      json.dump(state, f, indent=2)

    # Rename for atomic update
    temp_file.rename(self.state_file)

  def _create_config_files(self, protocol: str, address: Union[Path, Tuple[str, int]]) -> None:
    """
      Create configuration files for the Jupyter server.

      Parameters
      ----------
      protocol : str
          Protocol to use ('unix' or 'tcp')
      address : Union[Path, Tuple[str, int]]
          Address specification (socket path or host+port tuple)
      """
    # Generate a secure token and save to token file
    token = secrets.token_hex(32) # 64 character hex token
    with open(self.token_file, "w") as f:
      f.write(token)
    os.chmod(self.token_file, 0o600) # Restrict permissions

    # Generate a cookie secret and save to cookie secret file
    cookie_secret = secrets.token_bytes(32)
    with open(self.cookie_secret_file, "wb") as f:
      f.write(cookie_secret)
    os.chmod(self.cookie_secret_file, 0o600) # Restrict permissions

    # Create configuration file
    with open(self.config_file, "w") as f:
      f.write("# Jupyter Server Configuration\n\n")
      f.write("c = get_config()\n\n")

      # Basic configuration
      f.write("# Basic server configuration\n")
      f.write("c.ServerApp.open_browser = False\n")

      # Token and authentication
      f.write("\n# Authentication configuration\n")
      f.write(f"c.IdentityProvider.token = '{token}'\n")
      f.write(f"c.ServerApp.cookie_secret_file = '{self.cookie_secret_file}'\n")

      # Transport configuration
      f.write("\n# Transport configuration\n")
      if protocol == "unix":
        socket_path = address # address is Path for unix
        f.write(f"c.ServerApp.sock = '{socket_path}'\n")
        f.write(f"c.ServerApp.sock_mode = '0600'\n")
      else: # tcp
        host, port = address # address is (host, port) tuple for tcp
        f.write(f"c.ServerApp.ip = '{host}'\n")
        f.write(f"c.ServerApp.port = {port}\n")

      # Logging configuration
      f.write("\n# Logging configuration\n")
      f.write("c.Application.log_level = 'INFO'\n")

  def _safe_delete(self, path: Path) -> bool:
    """
      Safely delete a file if it exists.

      Parameters
      ----------
      path : Path
          Path to the file to delete

      Returns
      -------
      bool
          True if file was deleted or didn't exist, False on error
    """
    if not path.exists():
      return True

    try:
      path.unlink()
      return True
    except Exception as e:
      logger.error(f"Error deleting file {path}: {e}")
      return False

  def _test_connection(self, protocol: str, address: Union[Path, Tuple[str, int]]) -> bool:
    """
      Test server connectivity via socket connection.

      Parameters
      ----------
      protocol : str
          Transport protocol ('unix' or 'tcp')
      address : Union[Path, Tuple[str, int]]
          Socket path or (host, port) tuple

      Returns
      -------
      bool
          True if connection successful, False otherwise
    """
    try:
      if protocol == "unix":
        socket_path = address # address is Path for unix
        # For Unix socket, check if the socket file exists and is accessible
        if not socket_path.exists():
          return False

        # Try to connect to the socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(str(socket_path))
        sock.close()
        return True # Socket is accessible
      else: # tcp
        host, port = address # address is (host, port) tuple for tcp
        # For TCP, try to connect to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((host, port))
        sock.close()
        return True # Port is accessible
    except (socket.error, FileNotFoundError):
      # Socket/port not accessible
      return False

  def _wait_for_server_ready(self, server_url: str) -> None:
    """
      Wait for the server to be ready.

      Parameters
      ----------
      server_url : str
          Server URL specification

      Raises
      ------
      RuntimeError
          If server fails to start within timeout
    """
    # Parse server URL
    protocol, address = _parse_uri(server_url)

    # Define timeout parameters
    max_wait_time = 30 # seconds
    start_time = time.time()
    poll_interval = 0.5 # seconds

    # Wait for server to be ready
    while time.time() - start_time < max_wait_time:
      # Check if process is still running
      if not self._is_process_running():
        raise RuntimeError("Server process terminated unexpectedly")

      # Test connection
      if self._test_connection(protocol, address):
        return # Server is ready

      # Wait before trying again
      time.sleep(poll_interval)

    # Timeout expired
    self.down() # Attempt to shut down the server
    raise RuntimeError("Server failed to start within timeout")

  def _is_process_running(self) -> bool:
    """
      Check if the server process is still running.

      Returns
      -------
      bool
          True if process is running
    """
    state = self._load_state()
    pid = state.get("pid")

    if not pid:
      return False

    try:
      # Check if process exists by sending signal 0
      os.kill(pid, 0)
      return True
    except OSError:
      return False

  def _make_server_request(self, endpoint: str, token: Optional[str] = None) -> requests.Response:
    """
      Make a request to the server API.

      Parameters
      ----------
      endpoint : str
          API endpoint (e.g., "/api/status")
      token : Optional[str]
          Authentication token. If None, reads from token file.

      Returns
      -------
      requests.Response
          Response from server

      Raises
      ------
      Exception
          If request fails
    """
    state = self._load_state()
    connection_info = state.get("connection_info", {})

    # Get URI from connection info
    uri = connection_info.get("uri")
    if not uri:
      raise ValueError("No server URI in connection info")

    # Use provided token or read from file
    if token is None:
      try:
        token = self._get_token()
      except FileNotFoundError as e:
        raise ValueError("No token file available for server request") from e

    # Parse the URI
    protocol, address = _parse_uri(uri)

    # Create the HTTP URL
    if protocol == "unix":
      # For Unix socket HTTP, we'd need to use a Unix socket HTTP client
      # In a real implementation, you'd use a Unix socket HTTP client
      # For now, we'll raise an informative error
      raise NotImplementedError("HTTP over Unix sockets requires a specialized client. "
                                "Consider using a TCP connection for HTTP API access.")
    else: # tcp
      host, port = address # address is (host, port) tuple for tcp
      url = f"http://{host}:{port}{endpoint}"

    # Add token to URL if available
    if token:
      url = f"{url}?token={token}"

    # Make the request
    return requests.get(url, timeout=5)

  def _get_connection_info(self) -> Dict[str, Any]:
    """
      Get connection information for the running server.

      Returns
      -------
      Dict[str, Any]
          Connection information

      Raises
      ------
      RuntimeError
          If server is not running
    """
    if not self.is_running():
      raise RuntimeError("Server is not running")

    state = self._load_state()
    connection_info = state.get("connection_info")

    if not connection_info:
      raise RuntimeError("Connection information not available")

    return connection_info

  def _get_token(self) -> str:
    """
      Get the authentication token from the token file.

      Returns
      -------
      str
          Authentication token

      Raises
      ------
      FileNotFoundError
          If token file doesn't exist
    """
    if not self.token_file.exists():
      raise FileNotFoundError(f"Token file not found: {self.token_file}")

    with open(self.token_file, "r") as f:
      return f.read().strip()
