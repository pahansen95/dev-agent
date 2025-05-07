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
  logger.debug(f"Parsing URI: {uri}")
  parsed = urlparse(uri)
  protocol = parsed.scheme
  assert protocol in {"unix", "tcp"}, f"Unsupported protocol: {protocol}"

  if protocol == "unix":
    address = Path(parsed.path)
    logger.debug(f"Parsed unix socket path: {address}")
  else: # tcp
    if ":" in parsed.netloc:
      host, port_str = parsed.netloc.split(":")
      address = (host, int(port_str))
    else:
      host = parsed.netloc or "localhost"
      address = (host, 8888)
    logger.debug(f"Parsed TCP address: {address}")

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
    logger.debug(f"Initializing ServerController with base_dir: {base_dir}")
    
    # Convert to Path object if string
    self.base_dir = Path(base_dir)
    logger.debug(f"Base directory (normalized): {self.base_dir}")

    # Ensure base directory exists
    if not self.base_dir.exists():
      logger.error(f"Base directory does not exist: {self.base_dir}")
      raise ValueError(f"Base directory does not exist: {self.base_dir}")

    # Create hidden server state directory
    self.state_dir = self.base_dir / ".server"
    logger.debug(f"Creating state directory: {self.state_dir}")
    self.state_dir.mkdir(exist_ok=True)

    # Define paths for server files
    self.state_file = self.state_dir / "state.json"
    self.log_file = self.state_dir / "jupyter_server.log"
    self.socket_path = self.state_dir / "jupyter.sock"
    self.config_dir = self.state_dir / "config"
    logger.debug(f"Creating config directory: {self.config_dir}")
    self.config_dir.mkdir(exist_ok=True)
    self.config_file = self.config_dir / "jupyter_server_config.py"
    self.token_file = self.config_dir / "token"
    self.cookie_secret_file = self.config_dir / "cookie_secret"
    
    logger.debug(f"ServerController paths initialized:\n"
                f"  state_file: {self.state_file}\n"
                f"  log_file: {self.log_file}\n"
                f"  socket_path: {self.socket_path}\n"
                f"  config_file: {self.config_file}\n"
                f"  token_file: {self.token_file}\n"
                f"  cookie_secret_file: {self.cookie_secret_file}")

    # Initialize state
    self._initialize_state()
    logger.debug("ServerController initialization complete")

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
    logger.debug(f"ServerController.up(server_url={server_url!r}) called")
    
    # Check if server is already running
    if self.is_running():
      logger.info("Server already running")
      conn_info = self._get_connection_info()
      logger.debug(f"Returning existing connection info: {conn_info}")
      return conn_info

    # If no URL provided, use default socket path
    if server_url is None:
      server_url = f"unix://{self.socket_path}"
      logger.debug(f"No server_url provided, using default: {server_url}")

    # Parse server URL
    logger.debug(f"Parsing server URL: {server_url}")
    protocol, address = _parse_uri(server_url)
    logger.debug(f"Parsed server URL - protocol: {protocol}, address: {address}")

    # Create configuration files
    logger.debug("Creating configuration files")
    self._create_config_files(protocol, address)

    # Build command with proper arguments
    cmd = ["jupyter", "server"]
    cmd.extend(["--config", str(self.config_file)])
    logger.debug(f"Prepared server command: {' '.join(cmd)}")

    # Start the server process
    logger.info(f"Starting Jupyter server with command: {' '.join(cmd)}")
    server_start_time = time.time()

    try:
      with open(self.log_file, "wb") as log_file:
        process = subprocess.Popen(
          cmd,
          stdout=log_file,
          stderr=subprocess.STDOUT,
          start_new_session=True, # Create new process group
        )
      logger.debug(f"Server process started with PID: {process.pid}")
    except Exception as e:
      logger.error(f"Failed to start server process: {e}")
      self._save_state(
        running=False,
        last_error=str(e)
      )
      raise RuntimeError(f"Failed to start server process: {e}")

    # Create connection info
    connection_info = {"uri": server_url}
    logger.debug(f"Created connection info: {connection_info}")

    # Save initial state
    logger.debug(f"Saving server state with PID: {process.pid}")
    self._save_state(
      running=True,
      pid=process.pid,
      last_start_time=time.time(),
      connection_info=connection_info,
    )

    # Wait for server to be ready
    try:
      logger.debug("Waiting for server to be ready")
      self._wait_for_server_ready(server_url)
      server_startup_duration = time.time() - server_start_time
      logger.debug(f"Server ready after {server_startup_duration:.2f} seconds")
    except Exception as e:
      logger.error(f"Server failed to start: {e}")
      self._save_state(
        running=False,
        pid=None,
        connection_info=None,
        last_error=str(e)
      )
      # Try to clean up the process
      try:
        os.kill(process.pid, signal.SIGTERM)
        logger.debug(f"Sent SIGTERM to process {process.pid}")
      except OSError as kill_error:
        logger.debug(f"Error terminating process: {kill_error}")
      raise RuntimeError(f"Server failed to start: {e}")

    logger.debug(f"ServerController.up() completed successfully with URI: {connection_info['uri']}")
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
    logger.debug("ServerController.down() called")
    
    # Check if server is running
    if not self.is_running():
      logger.info("Server is not running")
      logger.debug("ServerController.down() returning False (server not running)")
      return False

    # Get server state
    state = self._load_state()
    pid = state.get("pid")

    if not pid:
      logger.warning("Server marked as running but no PID found")
      logger.debug("Updating state to reflect server not running")
      self._save_state(running=False)
      logger.debug("ServerController.down() returning False (no PID)")
      return False

    # Try graceful shutdown first
    logger.info(f"Stopping Jupyter server (PID: {pid})")
    logger.debug(f"Sending SIGTERM to process {pid}")

    try:
      # Try stopping using SIGTERM
      os.kill(pid, signal.SIGTERM)
      logger.debug(f"SIGTERM sent to process {pid}")

      # Wait for process to terminate
      shutdown_timeout = 10 # seconds
      shutdown_start = time.time()
      logger.debug(f"Waiting up to {shutdown_timeout} seconds for process to terminate")

      while time.time() - shutdown_start < shutdown_timeout:
        try:
          # Check if process exists by sending signal 0
          os.kill(pid, 0)
          # Process still exists, wait a bit
          logger.debug(f"Process {pid} still running, waiting...")
          time.sleep(0.5)
        except OSError:
          # Process no longer exists
          shutdown_duration = time.time() - shutdown_start
          logger.info(f"Server stopped gracefully after {shutdown_duration:.2f} seconds")
          logger.debug(f"Process {pid} terminated successfully")
          break
      else:
        # Timeout expired, force kill
        logger.warning(f"Server didn't terminate gracefully after {shutdown_timeout} seconds, forcing kill")
        try:
          logger.debug(f"Sending SIGKILL to process {pid}")
          os.kill(pid, signal.SIGKILL)
          logger.debug(f"SIGKILL sent to process {pid}")
        except OSError as e:
          logger.debug(f"Error sending SIGKILL: {e}")
          pass # Process might be gone already

    except OSError as e:
      logger.warning(f"Error stopping server: {e}")
      logger.debug(f"OSError when trying to signal process {pid}: {e}")
      # Process might be gone already

    # Update state
    logger.debug("Updating state to reflect server stopped")
    self._save_state(running=False, pid=None, connection_info=None)

    logger.debug("ServerController.down() returning True (server stopped)")
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
    logger.debug("ServerController.purge() called")
    
    # Stop the server if running
    if self.is_running():
      logger.debug("Server is running, stopping it first")
      self.down()

    # Remove server files
    logger.debug("Removing server files")
    files_to_delete = [
      self.log_file,
      self.state_file,
      self.socket_path,
      self.token_file,
      self.cookie_secret_file,
      self.config_file,
    ]
    
    delete_results = {}
    for file_path in files_to_delete:
      logger.debug(f"Attempting to delete: {file_path}")
      delete_results[str(file_path)] = self._safe_delete(file_path)
    
    success = all(delete_results.values())
    logger.debug(f"File deletion results: {delete_results}")

    # Re-initialize state
    logger.debug("Re-initializing state")
    self._initialize_state()

    logger.debug(f"ServerController.purge() returning {success}")
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
    logger.debug("ServerController.status() called")
    
    # Refresh running state
    is_running = self.is_running()
    logger.debug(f"Server running state: {is_running}")

    # Get current state
    state = self._load_state()
    logger.debug(f"Current state: {state}")

    # Prepare status report
    status = {
      "running": is_running,
      "pid": state.get("pid") if is_running else None,
      "connection_info": state.get("connection_info") if is_running else None,
      "last_start_time": state.get("last_start_time"),
      "last_error": state.get("last_error"),
    }
    
    logger.debug(f"Status report prepared: {status}")
    return status

  def is_running(self) -> bool:
    """
      Check if the Jupyter Server is running.

      Returns
      -------
      bool
          True if server is running and responsive
    """
    logger.debug("ServerController.is_running() called")
    
    # Check state file first
    state = self._load_state()
    if not state.get("running", False):
      logger.debug("State file indicates server is not running")
      return False

    # Verify process exists using helper method
    if not self._is_process_running():
      logger.debug("Process is not running, updating state")
      self._save_state(running=False, pid=None)
      return False

    # Get connection info
    connection_info = state.get("connection_info", {})
    if not connection_info:
      logger.debug("No connection info in state")
      return False

    # Get the URI
    uri = connection_info.get("uri")
    if not uri:
      logger.debug("No URI in connection info")
      return False

    # Parse the URI
    logger.debug(f"Testing connection with URI: {uri}")
    protocol, address = _parse_uri(uri)

    # Test socket connection
    connection_result = self._test_connection(protocol, address)
    logger.debug(f"Connection test result: {connection_result}")
    return connection_result

  # Private methods

  def _initialize_state(self) -> None:
    """
      Initialize or load the server state file.

      Creates a default state file if one doesn't exist.
    """
    logger.debug("Initializing server state")
    
    if not self.state_file.exists():
      logger.debug(f"State file not found: {self.state_file}")
      # Create default state
      default_state = {
        "running": False,
        "pid": None,
        "connection_info": None,
        "last_start_time": None,
        "last_error": None,
      }

      # Write state to file
      logger.debug(f"Creating default state file: {default_state}")
      with open(self.state_file, "w") as f:
        json.dump(default_state, f, indent=2)

    # Read current state
    state = self._load_state()
    logger.debug(f"Initial state loaded: {state}")

  def _load_state(self) -> Dict[str, Any]:
    """
      Load server state from state file.

      Returns
      -------
      Dict[str, Any]
          The current server state
    """
    logger.debug(f"Loading state from: {self.state_file}")
    try:
      with open(self.state_file, "r") as f:
        state = json.load(f)
      self._state = state
      logger.debug(f"State loaded successfully: {state}")
      return state
    except (json.JSONDecodeError, FileNotFoundError) as e:
      logger.warning(f"Error loading state file: {e}")
      logger.debug(f"Reinitializing state due to error: {e}")
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
    logger.debug(f"Saving state updates: {updates}")
    
    # Update state
    state = self._load_state()
    original_state = state.copy()
    state.update(updates)
    self._state = state
    
    # Log changes
    for key, new_value in updates.items():
      old_value = original_state.get(key)
      if old_value != new_value:
        logger.debug(f"State change: {key} = {old_value!r} -> {new_value!r}")

    # Write to temporary file first (atomic update)
    temp_file = self.state_file.with_suffix(".tmp")
    logger.debug(f"Writing state to temporary file: {temp_file}")
    with open(temp_file, "w") as f:
      json.dump(state, f, indent=2)

    # Rename for atomic update
    logger.debug(f"Renaming temporary file to: {self.state_file}")
    temp_file.rename(self.state_file)
    logger.debug("State saved successfully")

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
    logger.debug(f"Creating config files for protocol: {protocol}, address: {address}")
    
    # Generate a secure token and save to token file
    token = secrets.token_hex(32) # 64 character hex token
    logger.debug(f"Generated new authentication token (length: {len(token)})")
    
    with open(self.token_file, "w") as f:
      f.write(token)
    os.chmod(self.token_file, 0o600) # Restrict permissions
    logger.debug(f"Saved token to file: {self.token_file} (mode: 0o600)")

    # Generate a cookie secret and save to cookie secret file
    cookie_secret = secrets.token_bytes(32)
    logger.debug(f"Generated new cookie secret (length: {len(cookie_secret)})")
    
    with open(self.cookie_secret_file, "wb") as f:
      f.write(cookie_secret)
    os.chmod(self.cookie_secret_file, 0o600) # Restrict permissions
    logger.debug(f"Saved cookie secret to file: {self.cookie_secret_file} (mode: 0o600)")

    # Create configuration file
    logger.debug(f"Creating Jupyter server config file: {self.config_file}")
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
        logger.debug(f"Configured for Unix socket at: {socket_path}")
      else: # tcp
        host, port = address # address is (host, port) tuple for tcp
        f.write(f"c.ServerApp.ip = '{host}'\n")
        f.write(f"c.ServerApp.port = {port}\n")
        logger.debug(f"Configured for TCP on: {host}:{port}")

      # Logging configuration
      f.write("\n# Logging configuration\n")
      f.write("c.Application.log_level = 'INFO'\n")
    
    logger.debug("Config file generation complete")

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
    logger.debug(f"Safe delete requested for: {path}")
    
    if not path.exists():
      logger.debug(f"File does not exist: {path}")
      return True

    try:
      path.unlink()
      logger.debug(f"File deleted successfully: {path}")
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
    logger.debug(f"Testing connection: protocol={protocol}, address={address}")
    
    try:
      if protocol == "unix":
        socket_path = address # address is Path for unix
        # For Unix socket, check if the socket file exists and is accessible
        if not socket_path.exists():
          logger.debug(f"Unix socket does not exist: {socket_path}")
          return False

        # Try to connect to the socket
        logger.debug(f"Attempting to connect to Unix socket: {socket_path}")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(str(socket_path))
        sock.close()
        logger.debug("Unix socket connection successful")
        return True # Socket is accessible
      else: # tcp
        host, port = address # address is (host, port) tuple for tcp
        # For TCP, try to connect to the port
        logger.debug(f"Attempting to connect to TCP address: {host}:{port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((host, port))
        sock.close()
        logger.debug("TCP connection successful")
        return True # Port is accessible
    except (socket.error, FileNotFoundError) as e:
      # Socket/port not accessible
      logger.debug(f"Connection test failed: {e}")
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
    logger.debug(f"Waiting for server to be ready: {server_url}")
    
    # Parse server URL
    protocol, address = _parse_uri(server_url)
    logger.debug(f"Parsed server URL - protocol: {protocol}, address: {address}")

    # Define timeout parameters
    max_wait_time = 30 # seconds
    start_time = time.time()
    poll_interval = 0.5 # seconds
    logger.debug(f"Wait configuration: max_wait_time={max_wait_time}s, poll_interval={poll_interval}s")

    # Wait for server to be ready
    attempts = 0
    while time.time() - start_time < max_wait_time:
      attempts += 1
      elapsed = time.time() - start_time
      logger.debug(f"Connection attempt {attempts} at {elapsed:.2f}s")
      
      # Check if process is still running
      if not self._is_process_running():
        error_msg = "Server process terminated unexpectedly"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

      # Test connection
      if self._test_connection(protocol, address):
        logger.debug(f"Server ready after {elapsed:.2f}s and {attempts} attempts")
        return # Server is ready

      # Wait before trying again
      logger.debug(f"Server not ready yet, waiting {poll_interval}s before retry")
      time.sleep(poll_interval)

    # Timeout expired
    timeout_error = f"Server failed to start within timeout ({max_wait_time}s)"
    logger.error(timeout_error)
    logger.debug("Attempting to shut down the server due to timeout")
    self.down() # Attempt to shut down the server
    raise RuntimeError(timeout_error)

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
      logger.debug("No PID found in state")
      return False

    try:
      # Check if process exists by sending signal 0
      os.kill(pid, 0)
      logger.debug(f"Process {pid} is running")
      return True
    except OSError as e:
      logger.debug(f"Process {pid} is not running: {e}")
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
    logger.debug(f"Making server request to endpoint: {endpoint}")
    
    state = self._load_state()
    connection_info = state.get("connection_info", {})

    # Get URI from connection info
    uri = connection_info.get("uri")
    if not uri:
      error_msg = "No server URI in connection info"
      logger.error(error_msg)
      raise ValueError(error_msg)

    # Use provided token or read from file
    if token is None:
      try:
        logger.debug("No token provided, reading from token file")
        token = self._get_token()
        logger.debug(f"Token read from file (length: {len(token)})")
      except FileNotFoundError as e:
        error_msg = "No token file available for server request"
        logger.error(f"{error_msg}: {e}")
        raise ValueError(error_msg) from e

    # Parse the URI
    protocol, address = _parse_uri(uri)
    logger.debug(f"Parsed URI - protocol: {protocol}, address: {address}")

    # Create the HTTP URL
    if protocol == "unix":
      # For Unix socket HTTP, we'd need to use a Unix socket HTTP client
      # In a real implementation, you'd use a Unix socket HTTP client
      # For now, we'll raise an informative error
      error_msg = "HTTP over Unix sockets requires a specialized client. " \
                 "Consider using a TCP connection for HTTP API access."
      logger.error(error_msg)
      raise NotImplementedError(error_msg)
    else: # tcp
      host, port = address # address is (host, port) tuple for tcp
      url = f"http://{host}:{port}{endpoint}"
      logger.debug(f"Constructed HTTP URL: {url}")

    # Add token to URL if available
    if token:
      url = f"{url}?token={token}"
      logger.debug("Added authentication token to URL")

    # Make the request
    logger.debug(f"Sending HTTP request to: {url}")
    try:
      response = requests.get(url, timeout=5)
      logger.debug(f"Request successful: {response.status_code}")
      return response
    except Exception as e:
      logger.error(f"Request failed: {e}")
      raise

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
    logger.debug("Getting connection information")
    
    if not self.is_running():
      error_msg = "Server is not running"
      logger.error(error_msg)
      raise RuntimeError(error_msg)

    state = self._load_state()
    connection_info = state.get("connection_info")

    if not connection_info:
      error_msg = "Connection information not available"
      logger.error(error_msg)
      raise RuntimeError(error_msg)
    
    logger.debug(f"Connection information: {connection_info}")
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
    logger.debug(f"Getting authentication token from: {self.token_file}")
    
    if not self.token_file.exists():
      error_msg = f"Token file not found: {self.token_file}"
      logger.error(error_msg)
      raise FileNotFoundError(error_msg)

    with open(self.token_file, "r") as f:
      token = f.read().strip()
    
    logger.debug(f"Token retrieved successfully (length: {len(token)})")
    return token