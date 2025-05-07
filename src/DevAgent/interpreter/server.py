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
import ast
import json
import logging
import os
import secrets
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class _JupyterConfigManager:
    """
    Private class to manage Jupyter Server configuration.
    
    Handles:
    - Token generation and management
    - Cookie secret generation and management
    - Configuration file generation using string templates
    - Transport configuration for Unix sockets and TCP
    """
    
    def __init__(self, config_dir: Path, state_dir: Path):
        """
        Initialize the config manager.
        
        Parameters
        ----------
        config_dir : Path
            Directory for configuration files
        state_dir : Path
            Root directory for server state files
        """
        self.config_dir = config_dir
        self.state_dir = state_dir
        self.config_file = config_dir / "jupyter_server_config.py"
        self.token_file = config_dir / "token"
        self.cookie_secret_file = config_dir / "cookie_secret"
        self.socket_path = state_dir / "jupyter.sock"
    
    def _ensure_credential(self, file_path: Path, generate_func: Callable, binary: bool = False) -> str:
        """
        Generic method to handle credential generation/retrieval.
        
        Parameters
        ----------
        file_path : Path
            Path to the credential file
        generate_func : Callable
            Function that generates the credential
        binary : bool, default=False
            Whether to write in binary mode
            
        Returns
        -------
        str
            Path to the credential file
        """
        if not file_path.exists():
            logger.debug(f"Generating new credential: {file_path.name}")
            credential = generate_func()
            mode = "wb" if binary else "w"
            with open(file_path, mode) as f:
                f.write(credential)
            os.chmod(file_path, 0o600)
            logger.debug(f"Saved credential to: {file_path} (mode: 0o600)")
        else:
            logger.debug(f"Using existing credential: {file_path}")
        return str(file_path)
    
    def ensure_token(self) -> str:
        """
        Ensure a token exists, generating one if needed.
        
        Returns
        -------
        str
            Path to the token file
        """
        return self._ensure_credential(
            self.token_file,
            lambda: secrets.token_hex(32)
        )
    
    def ensure_cookie_secret(self) -> str:
        """
        Ensure a cookie secret exists, generating one if needed.
        
        Returns
        -------
        str
            Path to the cookie secret file
        """
        return self._ensure_credential(
            self.cookie_secret_file,
            lambda: secrets.token_bytes(32),
            binary=True
        )
    
    def _generate_common_config(self) -> str:
        """
        Generate the common configuration for all protocols.
        
        Returns
        -------
        str
            Common configuration template
        """
        return """
# Import required modules
import os

# Initialize configuration
c = get_config()

# Basic server configuration
c.ServerApp.open_browser = False

# Authentication configuration
token_path = os.path.join(os.path.dirname(__file__), 'token')
with open(token_path, 'r') as token_file:
    c.IdentityProvider.token = token_file.read().strip()

c.ServerApp.cookie_secret_file = os.path.join(os.path.dirname(__file__), 'cookie_secret')
"""
    
    def _generate_unix_config(self) -> str:
        """
        Generate configuration for Unix socket transport.
        
        Returns
        -------
        str
            Unix socket transport configuration
        """
        return """
# Transport configuration
sock_dir = os.path.dirname(os.path.dirname(__file__))
c.ServerApp.sock = os.path.join(sock_dir, 'jupyter.sock')
c.ServerApp.sock_mode = '0600'
"""
    
    def _generate_tcp_config(self, host: str, port: int) -> str:
        """
        Generate configuration for TCP transport.
        
        Parameters
        ----------
        host : str
            Hostname or IP address
        port : int
            Port number
            
        Returns
        -------
        str
            TCP transport configuration
        """
        return f"""
# Transport configuration
c.ServerApp.ip = '{host}'
c.ServerApp.port = {port}
"""
    
    def _generate_logging_config(self) -> str:
        """
        Generate logging configuration.
        
        Returns
        -------
        str
            Logging configuration
        """
        return """
# Logging configuration
c.Application.log_level = os.environ.get('LOG_LEVEL', 'INFO')
"""
    
    def generate_config(self, protocol: str, address: Union[Path, Tuple[str, int]]) -> str:
        """
        Generate the complete configuration.
        
        Parameters
        ----------
        protocol : str
            Transport protocol ('unix' or 'tcp')
        address : Union[Path, Tuple[str, int]]
            Address specification (socket path or host+port tuple)
            
        Returns
        -------
        str
            Complete configuration string
        """
        config = "# Jupyter Server Configuration\n"
        config += self._generate_common_config()
        
        if protocol == "unix":
            config += self._generate_unix_config()
        else:  # tcp
            host, port = address
            config += self._generate_tcp_config(host, port)
            
        config += self._generate_logging_config()
        return config
    
    def update_config(self, protocol: str, address: Union[Path, Tuple[str, int]]) -> None:
        """
        Update the configuration file if needed.
        
        Parameters
        ----------
        protocol : str
            Transport protocol ('unix' or 'tcp')
        address : Union[Path, Tuple[str, int]]
            Address specification (socket path or host+port tuple)
        """
        # Ensure credentials exist
        self.ensure_token()
        self.ensure_cookie_secret()
        
        # Generate the configuration
        config = self.generate_config(protocol, address)
        
        # Check if we need to update the config
        config_needs_update = True
        if self.config_file.exists():
            logger.debug(f"Config file already exists: {self.config_file}")
            # In a full implementation, we might check if the config has changed
            # by comparing the file content, but we'll always update for simplicity
        
        if config_needs_update:
            logger.debug(f"Writing configuration to: {self.config_file}")
            with open(self.config_file, "w") as f:
                f.write(config)
            logger.debug("Configuration file updated")
        else:
            logger.debug("Configuration file unchanged")


class ServerController:
    """
    Manages the lifecycle of a Jupyter Server process.
    
    This component is responsible for starting, stopping, and monitoring a Jupyter Server
    process. It handles configuration, process management, and provides status information.
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
        
        # Define directory structure
        self.state_dir = self.base_dir / ".server"
        self.config_dir = self.state_dir / "config"
        self.log_file = self.state_dir / "jupyter_server.log"
        self.state_file = self.state_dir / "state.json"
        
        # Ensure required directories exist
        self._ensure_directories()
        
        # Initialize the config manager
        self._config_manager = _JupyterConfigManager(self.config_dir, self.state_dir)
        
        # Initialize state
        self._initialize_state()
    
    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        logger.debug("Ensuring required directories exist")
        self.state_dir.mkdir(exist_ok=True)
        self.config_dir.mkdir(exist_ok=True)
    
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
    
    def up(self, server_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Ensure Jupyter Server is running, starting it if needed.
        
        Parameters
        ----------
        server_url : Optional[str]
            Server URL specification (unix:///path/to/socket.sock or tcp://host:port)
            If None, defaults to Unix socket in state directory
            
        Returns
        -------
        Dict[str, Any]
            Connection information including server URI
            
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
            socket_path = self._config_manager.socket_path
            server_url = f"unix://{socket_path}"
            logger.debug(f"No server_url provided, using default: {server_url}")
            
        # Parse server URL to determine protocol and address
        logger.debug(f"Parsing server URL: {server_url}")
        protocol, address = self._parse_uri(server_url)
        logger.debug(f"Parsed server URL - protocol: {protocol}, address: {address}")
        
        # Create/update configuration files
        logger.debug("Updating configuration files")
        self._create_config_files(protocol, address)
        
        # Build command with proper arguments
        cmd = ["jupyter", "server"]
        cmd.extend(["--config", str(self._config_manager.config_file)])
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
                    start_new_session=True,  # Create new process group
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
            logger.debug(f"Server failed to start", exc_info=True)
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
        
        Returns
        -------
        bool
            True if server was stopped, False if it was not running
        """
        logger.debug("ServerController.down() called")
        
        # Fetch current state
        state = self._load_state()
        
        # Check if server is running
        if not state.get("running", False):
            logger.info("Server is not running")
            return False
            
        pid = state.get("pid")
        if not pid:
            logger.warning("Server marked as running but no PID found")
            self._save_state(running=False)
            return False
            
        # Try graceful shutdown
        logger.info(f"Stopping Jupyter server (PID: {pid})")
        
        try:
            # Try stopping using SIGTERM
            os.kill(pid, signal.SIGTERM)
            logger.debug(f"SIGTERM sent to process {pid}")
            
            # Wait for process to terminate
            shutdown_timeout = 10  # seconds
            shutdown_start = time.time()
            
            while time.time() - shutdown_start < shutdown_timeout:
                try:
                    # Check if process exists
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
                    pass  # Process might be gone already
                    
        except OSError as e:
            logger.warning(f"Error stopping server: {e}")
            # Process might be gone already
            
        # Update state
        self._save_state(running=False, pid=None, connection_info=None)
        return True
    
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
            - last_start_time: float - Timestamp of last start
            - last_error: Optional[str] - Last error message
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
            
        # Verify process exists
        pid = state.get("pid")
        if not pid:
            return False
            
        try:
            # Check if process exists by sending signal 0
            os.kill(pid, 0)
        except OSError:
            # Process doesn't exist anymore
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
        protocol, address = self._parse_uri(uri)
        
        # Test socket connection
        return self._is_connection_available(protocol, address)
    
    def purge(self) -> bool:
        """
        Stop the server and remove all state.
        
        Returns
        -------
        bool
            True if purge was successful
        """
        # Stop the server if running
        if self.is_running():
            self.down()
            
        # Remove server files
        files_to_delete = [
            self.log_file,
            self.state_file,
            self._config_manager.socket_path,
            self._config_manager.token_file,
            self._config_manager.cookie_secret_file,
            self._config_manager.config_file,
        ]
        
        all_deleted = True
        for file_path in files_to_delete:
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
                    all_deleted = False
                    
        # Re-initialize state
        self._initialize_state()
        
        return all_deleted
    
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
        # Delegate to the config manager
        self._config_manager.update_config(protocol, address)
    
    def _parse_uri(self, uri: str) -> Tuple[str, Union[Path, Tuple[str, int]]]:
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
        """
        parsed = urlparse(uri)
        protocol = parsed.scheme
        assert protocol in {"unix", "tcp"}, f"Unsupported protocol: {protocol}"
        
        if protocol == "unix":
            address = Path(parsed.path)
        else:  # tcp
            if ":" in parsed.netloc:
                host, port_str = parsed.netloc.split(":")
                address = (host, int(port_str))
            else:
                host = parsed.netloc or "localhost"
                address = (host, 8888)
                
        return protocol, address
    
    def _is_connection_available(self, protocol: str, address: Union[Path, Tuple[str, int]], 
                               timeout: float = 1.0) -> bool:
        """
        Test if server connection is available with specified timeout.
        
        Parameters
        ----------
        protocol : str
            Transport protocol ('unix' or 'tcp')
        address : Union[Path, Tuple[str, int]]
            Socket path or (host, port) tuple
        timeout : float, default=1.0
            Socket connection timeout in seconds
            
        Returns
        -------
        bool
            True if connection successful, False otherwise
        """
        try:
            if protocol == "unix":
                socket_path = address  # address is Path for unix
                if not socket_path.exists():
                    return False
                    
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect(str(socket_path))
                sock.close()
                return True
                
            else:  # tcp
                host, port = address  # address is (host, port) tuple for tcp
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((host, port))
                sock.close()
                return True
                
        except (socket.error, FileNotFoundError):
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
        # Delegate to the standardized connection test method
        return self._is_connection_available(protocol, address)
    
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
        protocol, address = self._parse_uri(server_url)
        
        # Define timeout parameters
        max_wait_time = 30  # seconds
        start_time = time.time()
        poll_interval = 0.5  # seconds
        
        # Wait for server to be ready
        while time.time() - start_time < max_wait_time:
            # Check if process is still running
            if not self._is_process_running():
                raise RuntimeError("Server process terminated unexpectedly")
                
            # Test connection
            if self._is_connection_available(protocol, address):
                return  # Server is ready
                
            # Wait before trying again
            time.sleep(poll_interval)
            
        # Timeout expired
        raise RuntimeError(f"Server failed to start within timeout ({max_wait_time}s)")
    
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
            return state
        except (json.JSONDecodeError, FileNotFoundError):
            # Reinitialize state file
            self._initialize_state()
            with open(self.state_file, "r") as f:
                return json.load(f)
    
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
        
        # Write to temporary file first (atomic update)
        temp_file = self.state_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(state, f, indent=2)
            
        # Rename for atomic update
        temp_file.rename(self.state_file)
    
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
