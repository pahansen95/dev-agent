from typing import Dict, Optional, Any
import logging
from pathlib import Path

from ..domain.model import Kernel
from ..domain.value_objects import KernelId, SessionId, ExecutionResult
from ...interpreter.kernel import KernelController as LegacyKernelController
from ..kernel import KernelController

logger = logging.getLogger(__name__)

class KernelControllerAdapter:
    """
    Adapter that connects the domain Kernel model to the infrastructure KernelController.
    This allows the domain model to remain pure while delegating actual kernel
    operations to the existing implementation.
    """
    
    def __init__(self, base_dir: Path = None):
        """
        Initialize the adapter.
        
        Args:
            base_dir: Base directory for interpreter files, used for reconnection
        """
        self._controllers: Dict[str, LegacyKernelController] = {}
        self.base_dir = base_dir
    
    def get_controller(self, kernel: Kernel, workspace_dir: Path) -> LegacyKernelController:
        """
        Get or create a controller for the given kernel.
        
        Args:
            kernel: The kernel entity
            workspace_dir: The workspace directory for the kernel
            
        Returns:
            The kernel controller
        """
        kernel_id = str(kernel.id)
        
        # Check if we already have a controller
        if kernel_id in self._controllers:
            controller = self._controllers[kernel_id]
            if controller.is_alive():
                return controller
            else:
                # Remove dead controller
                del self._controllers[kernel_id]
        
        # Create new controller
        controller = LegacyKernelController(
            id=kernel_id,
            name=kernel.name,
            kernel_type=kernel.kernel_type,
            session_id=str(kernel.session_id),
            workspace_dir=workspace_dir
        )
        
        self._controllers[kernel_id] = controller
        return controller
    
    def create_controller(
        self, 
        kernel_id: str, 
        name: str, 
        kernel_type: str, 
        session_id: str, 
        workspace_dir: Path
    ) -> KernelController:
        """
        Create a new kernel controller.
        
        Args:
            kernel_id: The kernel ID
            name: The kernel name
            kernel_type: The kernel type
            session_id: The session ID
            workspace_dir: Path to the workspace directory
            
        Returns:
            The created kernel controller
        """
        # Ensure workspace directory exists
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Create controller
        controller = KernelController(
            id=kernel_id,
            name=name,
            kernel_type=kernel_type,
            session_id=session_id,
            workspace_dir=workspace_dir
        )
        
        return controller
    
    def reconnect_controller(self, kernel_id: str, connection_file: str) -> Optional[KernelController]:
        """
        Create a controller and reconnect to an existing kernel.
        
        Args:
            kernel_id: The kernel ID
            connection_file: Path to the connection file
            
        Returns:
            The reconnected kernel controller, or None if reconnection fails
        """
        try:
            # Create a workspace directory
            if self.base_dir:
                workspace_dir = self.base_dir / "runtime" / "workspaces" / kernel_id
            else:
                workspace_dir = Path(f"/tmp/devagent/workspaces/{kernel_id}")
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            # Get connection info from connection file
            connection_info = {
                "kernel_id": kernel_id,
                "connection_file": connection_file,
                # Other fields will be filled in by from_connection_info
                "name": "reconnected",
                "kernel_type": "unknown",
                "session_id": "unknown"
            }
            
            # Create controller from connection info
            controller = KernelController.from_connection_info(connection_info, workspace_dir)
            
            # Check if reconnection was successful
            if controller.is_alive():
                return controller
            else:
                logger.warning(f"Failed to reconnect to kernel {kernel_id}")
                return None
        except Exception as e:
            logger.error(f"Error reconnecting to kernel {kernel_id}: {e}")
            return None
    
    def start_kernel(self, kernel: Kernel, workspace_dir: Path) -> bool:
        """
        Start the kernel process.
        
        Args:
            kernel: The kernel entity
            workspace_dir: The workspace directory for the kernel
            
        Returns:
            True if started successfully, False otherwise
        """
        controller = self.get_controller(kernel, workspace_dir)
        success = controller.start_kernel()
        if success:
            kernel._is_alive = True
        return success
    
    def execute_code(self, kernel: Kernel, code: str, workspace_dir: Path) -> ExecutionResult:
        """
        Execute code in the kernel.
        
        Args:
            kernel: The kernel entity
            code: The code to execute
            workspace_dir: The workspace directory for the kernel
            
        Returns:
            The execution result
        """
        controller = self.get_controller(kernel, workspace_dir)
        
        # Execute using legacy controller
        legacy_result = controller.execute(code)
        
        # Map to domain ExecutionResult
        result = ExecutionResult(
            success=legacy_result.success,
            stdout=legacy_result.stdout,
            error=legacy_result.error,
            outputs=legacy_result.outputs,
            execution_time=legacy_result.execution_time
        )
        
        # Update kernel state
        kernel.update_last_activity()
        
        return result
    
    def interrupt_kernel(self, kernel: Kernel, workspace_dir: Path) -> bool:
        """
        Interrupt the kernel's execution.
        
        Args:
            kernel: The kernel entity
            workspace_dir: The workspace directory for the kernel
            
        Returns:
            True if interrupted successfully, False otherwise
        """
        controller = self.get_controller(kernel, workspace_dir)
        return controller.interrupt()
    
    def restart_kernel(self, kernel: Kernel, workspace_dir: Path) -> bool:
        """
        Restart the kernel.
        
        Args:
            kernel: The kernel entity
            workspace_dir: The workspace directory for the kernel
            
        Returns:
            True if restarted successfully, False otherwise
        """
        controller = self.get_controller(kernel, workspace_dir)
        success = controller.restart()
        kernel._is_alive = success
        return success
    
    def shutdown_kernel(self, kernel: Kernel, workspace_dir: Path) -> bool:
        """
        Shutdown the kernel.
        
        Args:
            kernel: The kernel entity
            workspace_dir: The workspace directory for the kernel
            
        Returns:
            True if shut down successfully, False otherwise
        """
        controller = self.get_controller(kernel, workspace_dir)
        success = controller.shutdown()
        if success:
            kernel._is_alive = False
            # Remove from controllers cache
            if str(kernel.id) in self._controllers:
                del self._controllers[str(kernel.id)]
        return success