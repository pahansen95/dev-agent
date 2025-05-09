from typing import Dict, Optional, Union, List
from pathlib import Path
import time
import logging

from .value_objects import SessionId, KernelId, Reference, ExecutionResult
from .model import Session, Kernel
from .exceptions import ReferenceResolutionError, KernelError, SessionError
from .events import CodeExecuted, KernelStarted, KernelShutdown, KernelInterrupted, KernelRestarted
from .repositories import SessionRepository, KernelRepository

logger = logging.getLogger(__name__)

class ReferenceResolutionService:
    """Service for resolving reference strings to domain objects."""
    
    def __init__(self, session_repo: SessionRepository, kernel_repo: KernelRepository):
        """
        Initialize the service.
        
        Args:
            session_repo: The session repository
            kernel_repo: The kernel repository
        """
        self.session_repo = session_repo
        self.kernel_repo = kernel_repo
    
    def resolve_reference(self, reference_string: str) -> Dict[str, Optional[Union[str, Path]]]:
        """
        Resolve a reference string to components.
        
        Args:
            reference_string: The reference string
            
        Returns:
            A dict with:
            - type: "session" or "kernel" or None
            - session_id: The session ID or None
            - kernel_id: The kernel ID or None
            - session_path: Path to the session directory or None
            - kernel_path: Path to the kernel directory or None
        """
        result = {
            "type": None, 
            "session_id": None, 
            "kernel_id": None, 
            "session_path": None, 
            "kernel_path": None
        }
        
        # Parse the reference
        parsed_ref = Reference.parse(reference_string)
        
        # Case 1: Kernel reference
        if parsed_ref.type == "kernel":
            # Direct kernel ID
            if parsed_ref.id_component and parsed_ref.id_component.startswith("kid-"):
                kernel = self.kernel_repo.find_by_id(KernelId(parsed_ref.id_component))
                if kernel:
                    result["type"] = "kernel"
                    result["kernel_id"] = str(kernel.id)
                    result["session_id"] = str(kernel.session_id)
                    return result
            
            # Session/Kernel name format
            if parsed_ref.name_component and "/" in reference_string:
                session_name, kernel_name = reference_string.split("/", 1)
                session = self.session_repo.find_by_name(session_name)
                
                if session:
                    result["type"] = "kernel"
                    result["session_id"] = str(session.id)
                    
                    # Look up the kernel
                    kernel = self.kernel_repo.find_by_name(session.id, kernel_name)
                    if kernel:
                        result["kernel_id"] = str(kernel.id)
                    
                    return result
        
        # Case 2: Session reference
        if parsed_ref.type == "session":
            # Session ID
            if parsed_ref.id_component and parsed_ref.id_component.startswith("sid-"):
                session = self.session_repo.find_by_id(SessionId(parsed_ref.id_component))
                if session:
                    result["type"] = "session"
                    result["session_id"] = str(session.id)
                    return result
            
            # Session name
            if parsed_ref.name_component:
                session = self.session_repo.find_by_name(parsed_ref.name_component)
                if session:
                    result["type"] = "session"
                    result["session_id"] = str(session.id)
                    return result
        
        return result
    
    def resolve_to_session(self, reference_string: str) -> Optional[Session]:
        """
        Resolve a reference string to a session.
        
        Args:
            reference_string: The reference string
            
        Returns:
            The session if found, None otherwise
        """
        ref_dict = self.resolve_reference(reference_string)
        if ref_dict["session_id"]:
            return self.session_repo.find_by_id(SessionId(ref_dict["session_id"]))
        return None
    
    def resolve_to_kernel(self, reference_string: str) -> Optional[Kernel]:
        """
        Resolve a reference string to a kernel.
        
        Args:
            reference_string: The reference string
            
        Returns:
            The kernel if found, None otherwise
        """
        ref_dict = self.resolve_reference(reference_string)
        if ref_dict["kernel_id"]:
            return self.kernel_repo.find_by_id(KernelId(ref_dict["kernel_id"]))
        return None

class KernelLifecycleService:
    """Service for managing kernel lifecycle operations."""
    
    def __init__(self, kernel_repo, kernel_adapter, event_bus, fs_manager):
        """
        Initialize the service.
        
        Args:
            kernel_repo: The kernel repository
            kernel_adapter: The kernel adapter
            event_bus: The event bus
            fs_manager: The filesystem manager
        """
        self.kernel_repo = kernel_repo
        self.kernel_adapter = kernel_adapter
        self.event_bus = event_bus
        self.fs_manager = fs_manager
    
    def start_kernel(self, kernel: Kernel) -> bool:
        """
        Start a kernel.
        
        Args:
            kernel: The kernel to start
            
        Returns:
            True if the kernel was started successfully, False otherwise
        """
        # Get workspace directory
        session_path = self.fs_manager.get_session_path(str(kernel.session_id))
        kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel.id))
        workspace_dir = kernel_path / "workspace"
        
        # Start kernel using adapter
        success = self.kernel_adapter.start_kernel(kernel, workspace_dir)
        
        if success:
            # Update repository
            self.kernel_repo.save(kernel)
            
            # Publish event
            self.event_bus.publish(KernelStarted(kernel.id, time.time()))
        
        return success
    
    def shutdown_kernel(self, kernel: Kernel) -> bool:
        """
        Shutdown a kernel.
        
        Args:
            kernel: The kernel to shut down
            
        Returns:
            True if the kernel was shut down successfully, False otherwise
        """
        # Get workspace directory
        session_path = self.fs_manager.get_session_path(str(kernel.session_id))
        kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel.id))
        workspace_dir = kernel_path / "workspace"
        
        # Shutdown kernel using adapter
        success = self.kernel_adapter.shutdown_kernel(kernel, workspace_dir)
        
        if success:
            # Update repository
            self.kernel_repo.save(kernel)
            
            # Publish event
            self.event_bus.publish(KernelShutdown(kernel.id, time.time()))
        
        return success
    
    def restart_kernel(self, kernel: Kernel) -> bool:
        """
        Restart a kernel.
        
        Args:
            kernel: The kernel to restart
            
        Returns:
            True if the kernel was restarted successfully, False otherwise
        """
        # Get workspace directory
        session_path = self.fs_manager.get_session_path(str(kernel.session_id))
        kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel.id))
        workspace_dir = kernel_path / "workspace"
        
        # Restart kernel using adapter
        success = self.kernel_adapter.restart_kernel(kernel, workspace_dir)
        
        if success:
            # Update repository
            self.kernel_repo.save(kernel)
            
            # Publish event
            self.event_bus.publish(KernelRestarted(kernel.id, time.time()))
        
        return success
    
    def interrupt_kernel(self, kernel: Kernel) -> bool:
        """
        Interrupt a kernel's execution.
        
        Args:
            kernel: The kernel to interrupt
            
        Returns:
            True if the kernel was interrupted successfully, False otherwise
        """
        # Get workspace directory
        session_path = self.fs_manager.get_session_path(str(kernel.session_id))
        kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel.id))
        workspace_dir = kernel_path / "workspace"
        
        # Interrupt kernel using adapter
        success = self.kernel_adapter.interrupt_kernel(kernel, workspace_dir)
        
        if success:
            # Update repository
            self.kernel_repo.save(kernel)
            
            # Publish event
            self.event_bus.publish(KernelInterrupted(kernel.id, time.time()))
        
        return success

class ExecutionService:
    """Service for executing code in kernels."""
    
    def __init__(self, kernel_repo, kernel_adapter, event_bus, fs_manager):
        """
        Initialize the service.
        
        Args:
            kernel_repo: The kernel repository
            kernel_adapter: The kernel adapter
            event_bus: The event bus
            fs_manager: The filesystem manager
        """
        self.kernel_repo = kernel_repo
        self.kernel_adapter = kernel_adapter
        self.event_bus = event_bus
        self.fs_manager = fs_manager
    
    def execute_code(self, kernel: Kernel, code: str) -> ExecutionResult:
        """
        Execute code in a kernel.
        
        Args:
            kernel: The kernel to execute code in
            code: The code to execute
            
        Returns:
            The execution result
            
        Raises:
            KernelError: If the kernel is not alive
        """
        if not kernel.is_alive:
            raise KernelError(f"Kernel {kernel.id} is not alive")
        
        # Get workspace directory
        session_path = self.fs_manager.get_session_path(str(kernel.session_id))
        kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel.id))
        workspace_dir = kernel_path / "workspace"
        
        # Execute code using adapter
        result = self.kernel_adapter.execute_code(kernel, code, workspace_dir)
        
        # Update repository
        self.kernel_repo.save(kernel)
        
        # Publish event
        self.event_bus.publish(CodeExecuted(
            kernel_id=kernel.id,
            success=result.success,
            execution_time=result.execution_time,
            timestamp=time.time()
        ))
        
        return result