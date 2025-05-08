"""
The Dev Agent's API

Provides a clean interface to the ontology graph and kernel management.
"""
from __future__ import annotations
from .ontology import OntologyGraph, Node, Stage
from .interpreter import ServerController, SessionManager
from .core import *
import os, atexit, time

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
    controller = ServerController(pathlib.Path(base_dir))
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

class InterpreterSessionAPI:

  """
    API for managing DevAgent interpreter sessions.
    
    This provides a clean interface for session management operations,
    abstracting the underlying implementation details.
    """

  def __init__(self, base_dir: Optional[Union[str, Path]] = None):
    """
    Initialize the session API.
    
    Parameters
    ----------
    base_dir : str or Path, optional
        Base directory for session storage
    """

    self.base_dir = Path(base_dir or os.getcwd())
    # Ensure the base directory exists
    os.makedirs(self.base_dir, exist_ok=True)
    self.session_manager = SessionManager(self.base_dir)
    logger.info(f"Initialized InterpreterSessionAPI with base_dir={self.base_dir}")

  def create_session(self, session_id: str = "main", kernel_name: str = "python3") -> Dict[str, Any]:
    """
        Create a new session or return existing one.
        
        Parameters
        ----------
        session_id : str
            Unique identifier for the session (default: "main")
        kernel_name : str
            Name of the kernel to use (default: "python3")
            
        Returns
        -------
        Dict[str, Any]
            Session information dictionary
        """
    try:
      session = self.session_manager.create_session(session_id, kernel_name)
      return self._session_to_dict(session)
    except Exception as e:
      logger.error(f"Error creating session {session_id}: {str(e)}")
      return {"id": session_id, "error": str(e), "success": False}

  def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
    """
        Get information about an existing session.
        
        Parameters
        ----------
        session_id : str
            Unique identifier for the session
            
        Returns
        -------
        Optional[Dict[str, Any]]
            Session information dictionary or None if not found
        """
    session = self.session_manager.get_session(session_id)
    if session:
      return self._session_to_dict(session)
    return None

  def list_sessions(self) -> List[Dict[str, Any]]:
    """
        List all available sessions.
        
        Returns
        -------
        List[Dict[str, Any]]
            List of session information dictionaries
        """
    sessions = []
    for session_id in self.session_manager.list_sessions():
      session = self.session_manager.get_session(session_id)
      if session:
        sessions.append(self._session_to_dict(session))
    return sessions

  def execute(self, code: str, session_id: str = "main") -> Dict[str, Any]:
    """
        Execute code in a session.
        
        Parameters
        ----------
        code : str
            Code to execute
        session_id : str
            Session identifier (default: "main")
            
        Returns
        -------
        Dict[str, Any]
            Execution result with stdout, error, and success fields
        """
    # Get or create session
    session = self.session_manager.get_session(session_id)
    if not session:
      logger.info(f"Session {session_id} not found, creating it")
      session = self.session_manager.create_session(session_id)

    # Execute code
    try:
      logger.debug(f"Executing code in session {session_id}")
      start_time = time.time()
      stdout, error = session.execute(code)
      execution_time = time.time() - start_time

      return {"stdout": stdout, "error": error, "success": error is None, "execution_time": execution_time}
    except Exception as e:
      logger.error(f"Error executing code in session {session_id}: {str(e)}")
      return {"stdout": "", "error": str(e), "success": False, "execution_time": time.time() - start_time}

  def interrupt(self, session_id: str) -> Dict[str, Any]:
    """
        Interrupt execution in a session.
        
        Parameters
        ----------
        session_id : str
            Session identifier
            
        Returns
        -------
        Dict[str, Any]
            Result dictionary with success field
        """
    session = self.session_manager.get_session(session_id)
    if not session:
      logger.warning(f"Cannot interrupt - session {session_id} not found")
      return {"success": False, "error": f"Session {session_id} not found"}

    try:
      result = session.interrupt()
      return {"success": result}
    except Exception as e:
      logger.error(f"Error interrupting session {session_id}: {str(e)}")
      return {"success": False, "error": str(e)}

  def restart(self, session_id: str) -> Dict[str, Any]:
    """
        Restart a session's kernel.
        
        Parameters
        ----------
        session_id : str
            Session identifier
            
        Returns
        -------
        Dict[str, Any]
            Result dictionary with success field
        """
    session = self.session_manager.get_session(session_id)
    if not session:
      logger.warning(f"Cannot restart - session {session_id} not found")
      return {"success": False, "error": f"Session {session_id} not found"}

    try:
      result = session.restart()
      return {"success": result, "session": self._session_to_dict(session) if result else None}
    except Exception as e:
      logger.error(f"Error restarting session {session_id}: {str(e)}")
      return {"success": False, "error": str(e)}

  def delete_session(self, session_id: str) -> Dict[str, Any]:
    """
        Delete a session.
        
        Parameters
        ----------
        session_id : str
            Session identifier
            
        Returns
        -------
        Dict[str, Any]
            Result dictionary with success field
        """
    try:
      result = self.session_manager.shutdown_session(session_id)
      return {"success": result}
    except Exception as e:
      logger.error(f"Error deleting session {session_id}: {str(e)}")
      return {"success": False, "error": str(e)}

  def shutdown(self) -> Dict[str, Any]:
    """
        Shut down all sessions.
        
        Returns
        -------
        Dict[str, Any]
            Result dictionary with success field
        """
    try:
      session_count = len(self.session_manager.list_sessions())
      self.session_manager.shutdown()
      return {"success": True, "sessions_closed": session_count}
    except Exception as e:
      logger.error(f"Error shutting down sessions: {str(e)}")
      return {"success": False, "error": str(e)}

  def _session_to_dict(self, session) -> Dict[str, Any]:
    """
        Convert a Session object to a dictionary representation.
        
        Parameters
        ----------
        session : Session
            Session object
            
        Returns
        -------
        Dict[str, Any]
            Dictionary with session information
        """
    return {
      "id": session.id,
      "kernel_alive": session.kernel is not None and session.kernel.is_alive(),
      "kernel_name": session.kernel.kernel_name if session.kernel else None,
      "session_dir": str(session.session_dir),
      "last_activity": self._get_last_activity(session)
    }

  def _get_last_activity(self, session) -> Optional[float]:
    """
        Get the last activity timestamp from a session.
        
        Parameters
        ----------
        session : Session
            Session object
            
        Returns
        -------
        Optional[float]
            Timestamp of last activity or None
        """
    try:
      state = session._load_state()
      return state.get("last_activity")
    except:
      return None

# Public module surface
__all__ = [
  "OntologyAPI",
  "InterpreterServerAPI",
  "InterpreterSessionAPI",
]
