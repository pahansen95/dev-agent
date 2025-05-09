import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

from .application.facade import InterpreterFacade
from .infrastructure.event_bus import EventBus
from .infrastructure.fs_manager import FileSystemManager
from .infrastructure.repositories import FileSystemSessionRepository, FileSystemKernelRepository
from .infrastructure.kernel_adapter import KernelControllerAdapter
from .domain.services import ReferenceResolutionService, KernelLifecycleService, ExecutionService
from .domain.factories import SessionFactory, KernelFactory
from .application.app_service import InterpreterApplicationService

# Import legacy API
from .. import api

logger = logging.getLogger(__name__)

class DualModeInterpreter:
    """
    Compatibility layer that can operate in both old and new mode.
    This allows for a gradual migration from the old architecture to the new DDD architecture.
    """
    
    def __init__(self, base_dir: Path, use_ddd: bool = True):
        """
        Initialize the dual-mode interpreter.
        
        Args:
            base_dir: The base directory for interpreter files
            use_ddd: Whether to use the new DDD-based architecture (default: True)
        """
        self.base_dir = base_dir
        self.use_ddd = use_ddd
        
        # Flag file to control mode
        self.flag_file = base_dir / ".use_ddd"
        
        # Initialize based on flag file or parameter
        if self.flag_file.exists():
            self.use_ddd = True
        elif use_ddd:
            # Create flag file
            self.flag_file.touch()
        
        # Initialize appropriate implementation
        if self.use_ddd:
            # Initialize DDD-based implementation
            self.ddd_interpreter = self._create_ddd_interpreter()
            self.legacy_interpreter = None
        else:
            # Initialize legacy implementation
            self.legacy_interpreter = api.InterpreterAPI(base_dir)
            self.ddd_interpreter = None
    
    def _create_ddd_interpreter(self) -> InterpreterFacade:
        """
        Create the DDD-based interpreter with all dependencies.
        
        Returns:
            The interpreter facade
        """
        # Create infrastructure components
        fs_manager = FileSystemManager(self.base_dir)
        fs_manager.ensure_directory_structure()
        
        event_bus = EventBus()
        
        # Create repositories
        session_repo = FileSystemSessionRepository(fs_manager, event_bus)
        kernel_repo = FileSystemKernelRepository(fs_manager, event_bus)
        
        # Create domain services
        reference_service = ReferenceResolutionService(session_repo, kernel_repo)
        
        # Create factories
        session_factory = SessionFactory(session_repo, event_bus)
        kernel_factory = KernelFactory(kernel_repo, event_bus)
        
        # Create kernel adapter
        kernel_adapter = KernelControllerAdapter()
        
        # Create execution and lifecycle services
        kernel_lifecycle_service = KernelLifecycleService(kernel_repo, kernel_adapter, event_bus, fs_manager)
        execution_service = ExecutionService(kernel_repo, kernel_adapter, event_bus, fs_manager)
        
        # Create application service
        app_service = InterpreterApplicationService(
            session_repo=session_repo,
            kernel_repo=kernel_repo,
            session_factory=session_factory,
            kernel_factory=kernel_factory,
            reference_service=reference_service,
            execution_service=execution_service,
            kernel_lifecycle_service=kernel_lifecycle_service,
            fs_manager=fs_manager
        )
        
        # Create and return facade
        return InterpreterFacade(app_service)
    
    def set_mode(self, use_ddd: bool) -> None:
        """
        Change the operating mode.
        
        Args:
            use_ddd: Whether to use the new DDD-based architecture
        """
        if use_ddd == self.use_ddd:
            return
        
        # Update mode
        self.use_ddd = use_ddd
        
        # Update flag file
        if use_ddd:
            self.flag_file.touch()
        elif self.flag_file.exists():
            self.flag_file.unlink()
        
        # Reinitialize
        if use_ddd:
            # Initialize DDD-based implementation
            self.ddd_interpreter = self._create_ddd_interpreter()
            self.legacy_interpreter = None
        else:
            # Initialize legacy implementation
            self.legacy_interpreter = api.InterpreterAPI(self.base_dir)
            self.ddd_interpreter = None
    
    # Delegate methods to appropriate implementation
    def create_session(self, name: str) -> Dict[str, Any]:
        """
        Create a new session.
        
        Args:
            name: The session name
            
        Returns:
            A dictionary with the session ID if successful
        """
        if self.use_ddd:
            return self.ddd_interpreter.create_session(name)
        else:
            try:
                session = self.legacy_interpreter.create_session(name)
                return {
                    "success": True,
                    "session_id": session.id,
                    "error": None
                }
            except Exception as e:
                logger.exception(f"Error creating session: {e}")
                return {
                    "success": False,
                    "session_id": None,
                    "error": str(e)
                }
    
    def get_session(self, reference: str) -> Dict[str, Any]:
        """
        Get a session by reference.
        
        Args:
            reference: The session reference (name or ID)
            
        Returns:
            A dictionary with the session if found
        """
        if self.use_ddd:
            return self.ddd_interpreter.get_session(reference)
        else:
            try:
                session = self.legacy_interpreter.get_session(reference)
                if not session:
                    return {
                        "success": False,
                        "session": None,
                        "error": f"Session not found: {reference}"
                    }
                
                return {
                    "success": True,
                    "session": {
                        "id": session.id,
                        "name": session.name,
                        "created_at": session.created_at,
                        "last_activity": session.last_activity,
                        "kernel_count": len(session.kernels),
                        "path": str(session.path)
                    },
                    "error": None
                }
            except Exception as e:
                logger.exception(f"Error getting session: {e}")
                return {
                    "success": False,
                    "session": None,
                    "error": str(e)
                }
    
    def list_sessions(self) -> Dict[str, Any]:
        """
        List all sessions.
        
        Returns:
            A dictionary with all sessions
        """
        if self.use_ddd:
            return self.ddd_interpreter.list_sessions()
        else:
            try:
                sessions = self.legacy_interpreter.list_sessions()
                return {
                    "success": True,
                    "sessions": [
                        {
                            "id": s.id,
                            "name": s.name,
                            "created_at": s.created_at,
                            "last_activity": s.last_activity,
                            "kernel_count": len(s.kernels),
                            "path": str(s.path)
                        }
                        for s in sessions
                    ],
                    "error": None
                }
            except Exception as e:
                logger.exception(f"Error listing sessions: {e}")
                return {
                    "success": False,
                    "sessions": [],
                    "error": str(e)
                }
    
    def delete_session(self, reference: str) -> Dict[str, Any]:
        """
        Delete a session.
        
        Args:
            reference: The session reference (name or ID)
            
        Returns:
            A dictionary indicating success or failure
        """
        if self.use_ddd:
            return self.ddd_interpreter.delete_session(reference)
        else:
            try:
                success = self.legacy_interpreter.delete_session(reference)
                return {
                    "success": success,
                    "error": None if success else f"Failed to delete session: {reference}"
                }
            except Exception as e:
                logger.exception(f"Error deleting session: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
    
    def create_kernel(self, session_reference: str, kernel_name: str, kernel_type: str = "python3") -> Dict[str, Any]:
        """
        Create a new kernel in a session.
        
        Args:
            session_reference: The session reference (name or ID)
            kernel_name: The kernel name
            kernel_type: The kernel type (default: "python3")
            
        Returns:
            A dictionary with the kernel ID if successful
        """
        if self.use_ddd:
            return self.ddd_interpreter.create_kernel(session_reference, kernel_name, kernel_type)
        else:
            try:
                kernel = self.legacy_interpreter.create_kernel(session_reference, kernel_name, kernel_type)
                return {
                    "success": True,
                    "kernel_id": kernel.id,
                    "error": None
                }
            except Exception as e:
                logger.exception(f"Error creating kernel: {e}")
                return {
                    "success": False,
                    "kernel_id": None,
                    "error": str(e)
                }
    
    def get_kernel(self, reference: str) -> Dict[str, Any]:
        """
        Get a kernel by reference.
        
        Args:
            reference: The kernel reference
            
        Returns:
            A dictionary with the kernel if found
        """
        if self.use_ddd:
            return self.ddd_interpreter.get_kernel(reference)
        else:
            try:
                kernel = self.legacy_interpreter.get_kernel(reference)
                if not kernel:
                    return {
                        "success": False,
                        "kernel": None,
                        "error": f"Kernel not found: {reference}"
                    }
                
                session = self.legacy_interpreter.get_session(kernel.session_id)
                session_name = session.name if session else kernel.session_id
                
                return {
                    "success": True,
                    "kernel": {
                        "id": kernel.id,
                        "name": kernel.name,
                        "kernel_type": kernel.kernel_type,
                        "session_id": kernel.session_id,
                        "session_name": session_name,
                        "is_alive": kernel.is_alive(),
                        "created_at": kernel.created_at,
                        "last_activity": kernel.last_activity,
                        "path": str(kernel.path)
                    },
                    "error": None
                }
            except Exception as e:
                logger.exception(f"Error getting kernel: {e}")
                return {
                    "success": False,
                    "kernel": None,
                    "error": str(e)
                }
    
    def execute_code(self, reference: str, code: str) -> Dict[str, Any]:
        """
        Execute code in a kernel.
        
        Args:
            reference: The kernel reference
            code: The code to execute
            
        Returns:
            A dictionary with the execution result
        """
        if self.use_ddd:
            return self.ddd_interpreter.execute_code(reference, code)
        else:
            try:
                result = self.legacy_interpreter.execute(reference, code)
                return {
                    "success": result.success,
                    "stdout": result.stdout,
                    "error": result.error,
                    "outputs": result.outputs,
                    "execution_time": result.execution_time
                }
            except Exception as e:
                logger.exception(f"Error executing code: {e}")
                return {
                    "success": False,
                    "stdout": "",
                    "error": str(e),
                    "outputs": [],
                    "execution_time": 0.0
                }