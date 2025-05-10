from typing import Dict, Optional, Any
import logging
from pathlib import Path

from jupyter_client import KernelManager

from ..domain.model import Kernel
from ..domain.value_objects import KernelId, SessionId, ExecutionResult
from ...interpreter.kernel import KernelController as LegacyKernelController
from ..kernel import KernelController
from .fs_manager import FileSystemManager
from .repositories import FileSystemRuntimeStateRepository

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
        logger.debug(f"Using cached controller for kernel {kernel_id}")
        return controller
      else:
        # Remove dead controller
        logger.info(f"Removing dead controller for kernel {kernel_id}")
        del self._controllers[kernel_id]

    # Try to reconnect to an existing kernel
    runtime_repo = FileSystemRuntimeStateRepository(FileSystemManager(self.base_dir), None)
    runtime_state = runtime_repo.find_by_kernel_id(kernel.id)

    if runtime_state and runtime_state.connection_file:
        logger.info(f"Attempting to reconnect to kernel {kernel_id} using connection file")
        try:
            # Try to reconnect using the controller's from_connection_info method
            connection_info = {
                "kernel_id": kernel_id,
                "name": kernel.name,
                "kernel_type": kernel.kernel_type,
                "session_id": str(kernel.session_id),
                "jupyter_kernel_id": runtime_state.jupyter_kernel_id,
                "connection_file": runtime_state.connection_file
            }

            controller = LegacyKernelController.from_connection_info(connection_info, workspace_dir)

            # If reconnection was successful, save it in our cache
            if controller and controller.is_alive():
                logger.info(f"Successfully reconnected to kernel: {controller.id}")
                self._controllers[kernel_id] = controller
                return controller
            else:
                logger.warning(f"Reconnection to kernel {kernel_id} failed, will create new controller")
        except Exception as e:
            logger.error(f"Error reconnecting to kernel {kernel_id}: {e}")

    # Create new controller
    logger.info(f"Creating new controller for kernel {kernel_id}")
    controller = LegacyKernelController(
      id=kernel_id, name=kernel.name, kernel_type=kernel.kernel_type, session_id=str(kernel.session_id), workspace_dir=workspace_dir)

    self._controllers[kernel_id] = controller
    return controller

  def create_controller(self, kernel_id: str, name: str, kernel_type: str, session_id: str, workspace_dir: Path) -> KernelController:
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
    controller = KernelController(id=kernel_id, name=name, kernel_type=kernel_type, session_id=session_id, workspace_dir=workspace_dir)

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
    # Try to get the controller first (might be cached)
    controller = None

    # Get runtime state for connection info regardless of whether we have a controller
    # This ensures we always have the latest kernel state information
    runtime_repo = FileSystemRuntimeStateRepository(FileSystemManager(self.base_dir), None)
    runtime_state = runtime_repo.find_by_kernel_id(kernel.id)

    # Check if we have a controller and if it's alive
    if str(kernel.id) in self._controllers:
        controller = self._controllers[str(kernel.id)]
        if not controller.is_alive() and runtime_state and runtime_state.connection_file:
            # Controller exists but is not alive, remove it so we can reconnect properly
            logger.info(f"Cached controller for kernel {kernel.id} is not alive, will reconnect")
            del self._controllers[str(kernel.id)]
            controller = None

    # If no controller exists or it was removed because it wasn't alive, try to reconnect
    if controller is None and runtime_state and runtime_state.connection_file:
        logger.info(f"Attempting to reconnect to kernel {kernel.id} using connection file: {runtime_state.connection_file}")
        try:
            # Try to reconnect using the new controller's from_connection_info method
            connection_info = {
                "kernel_id": str(kernel.id),
                "name": kernel.name,
                "kernel_type": kernel.kernel_type,
                "session_id": str(kernel.session_id),
                "jupyter_kernel_id": runtime_state.jupyter_kernel_id,
                "connection_file": runtime_state.connection_file
            }

            controller = LegacyKernelController.from_connection_info(connection_info, workspace_dir)

            # If reconnection was successful, save it in our cache
            if controller and controller.is_alive():
                logger.info(f"Successfully reconnected to kernel: {controller.id}")
                self._controllers[str(kernel.id)] = controller
            else:
                logger.warning(f"Reconnection to kernel {kernel.id} returned controller but kernel is not alive")
                controller = None
        except Exception as e:
            logger.error(f"Error reconnecting to kernel {kernel.id}: {e}")
            controller = None

    # If we still don't have a controller or it's not alive, create a new one
    if controller is None or not controller.is_alive():
        logger.info(f"Creating new controller for kernel {kernel.id}")
        controller = LegacyKernelController(
          id=str(kernel.id),
          name=kernel.name,
          kernel_type=kernel.kernel_type,
          session_id=str(kernel.session_id),
          workspace_dir=workspace_dir)

        # Try to start the kernel
        logger.info(f"Attempting to start kernel {kernel.id}")
        if controller.start_kernel():
            logger.info(f"Successfully started kernel {controller.id}")
            self._controllers[str(kernel.id)] = controller

            # Update runtime state with new connection info if we have a runtime repo
            if runtime_state:
                runtime_state.connection_file = controller.connection_file
                runtime_state.jupyter_kernel_id = controller.jupyter_kernel_id
                runtime_state.process_id = None  # Will be updated by the process observer
                runtime_repo.save(runtime_state)
        else:
            logger.error(f"Failed to start kernel {kernel.id}")
            return ExecutionResult(
                success=False,
                error=f"Failed to start or connect to kernel {kernel.id}",
                stdout="",
                outputs=[],
                execution_time=0.0
            )

    # Execute using controller
    try:
        # Double check that controller is alive before executing
        if not controller.is_alive():
            return ExecutionResult(
                success=False,
                error=f"Kernel {kernel.id} is not alive even after reconnection/restart attempts",
                stdout="",
                outputs=[],
                execution_time=0.0
            )

        legacy_result = controller.execute(code)

        # Map to domain ExecutionResult
        result = ExecutionResult(
            success=legacy_result.success,
            stdout=legacy_result.stdout,
            error=legacy_result.error,
            outputs=legacy_result.outputs,
            execution_time=legacy_result.execution_time)

        # Update kernel state
        kernel.update_last_activity()

        return result
    except Exception as e:
        logger.error(f"Error executing code in kernel {controller.id}: {e}")
        return ExecutionResult(
            success=False,
            error=str(e),
            stdout="",
            outputs=[],
            execution_time=0.0
        )

  def interrupt_kernel(self, kernel: Kernel, workspace_dir: Path) -> bool:
    """
        Interrupt the kernel's execution.

        Args:
            kernel: The kernel entity
            workspace_dir: The workspace directory for the kernel

        Returns:
            True if interrupted successfully, False otherwise
        """
    logger.info(f"Interrupting kernel {kernel.id}")

    # Get controller, this will try to reconnect if needed
    controller = self.get_controller(kernel, workspace_dir)

    # Check if kernel is alive
    if not controller.is_alive():
        logger.warning(f"Cannot interrupt kernel {kernel.id}: not alive")
        return False

    # Try to interrupt
    success = controller.interrupt()

    if success:
        logger.info(f"Successfully interrupted kernel {kernel.id}")
    else:
        logger.warning(f"Failed to interrupt kernel {kernel.id}")

    return success

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

    # Try to restart the kernel
    logger.info(f"Restarting kernel {kernel.id}")
    success = controller.restart()

    if success:
        # Update runtime state with new connection info if available
        if hasattr(controller, 'connection_file') and controller.connection_file:
            runtime_repo = FileSystemRuntimeStateRepository(FileSystemManager(self.base_dir), None)
            runtime_state = runtime_repo.find_by_kernel_id(kernel.id)

            if runtime_state:
                runtime_state.connection_file = controller.connection_file
                if hasattr(controller, 'jupyter_kernel_id'):
                    runtime_state.jupyter_kernel_id = controller.jupyter_kernel_id
                runtime_repo.save(runtime_state)

        # Update kernel state
        kernel._is_alive = True
    else:
        # If restart failed, try to start a new kernel
        logger.warning(f"Failed to restart kernel {kernel.id}, attempting to start fresh")

        # Clear controller from cache
        if str(kernel.id) in self._controllers:
            del self._controllers[str(kernel.id)]

        # Try to start a new kernel
        success = self.start_kernel(kernel, workspace_dir)

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
    logger.info(f"Shutting down kernel {kernel.id}")

    # Try to get controller first
    controller = None
    if str(kernel.id) in self._controllers:
        controller = self._controllers[str(kernel.id)]

    # If no controller in cache, check if we need to reconnect first
    if controller is None:
        runtime_repo = FileSystemRuntimeStateRepository(FileSystemManager(self.base_dir), None)
        runtime_state = runtime_repo.find_by_kernel_id(kernel.id)

        # If we have connection info, try to reconnect before shutting down
        if runtime_state and runtime_state.connection_file:
            logger.info(f"Attempting to reconnect to kernel {kernel.id} before shutdown")
            try:
                connection_info = {
                    "kernel_id": str(kernel.id),
                    "name": kernel.name,
                    "kernel_type": kernel.kernel_type,
                    "session_id": str(kernel.session_id),
                    "jupyter_kernel_id": runtime_state.jupyter_kernel_id,
                    "connection_file": runtime_state.connection_file
                }

                controller = LegacyKernelController.from_connection_info(connection_info, workspace_dir)
            except Exception as e:
                logger.error(f"Error reconnecting to kernel {kernel.id} for shutdown: {e}")

    # If we still don't have a controller, create one
    if controller is None:
        controller = LegacyKernelController(
            id=str(kernel.id),
            name=kernel.name,
            kernel_type=kernel.kernel_type,
            session_id=str(kernel.session_id),
            workspace_dir=workspace_dir)

    # Attempt to shut down the kernel
    success = controller.shutdown()

    # Update kernel state
    if success:
        logger.info(f"Successfully shut down kernel {kernel.id}")
        kernel._is_alive = False

        # Update runtime state to indicate kernel is stopped
        runtime_repo = FileSystemRuntimeStateRepository(FileSystemManager(self.base_dir), None)
        runtime_state = runtime_repo.find_by_kernel_id(kernel.id)
        if runtime_state:
            # We don't delete the runtime state here - that's the job of the operator
            # Just update it to indicate the kernel is no longer alive
            from ..domain.value_objects import KernelStatus
            runtime_state.status = KernelStatus.STOPPED
            runtime_repo.save(runtime_state)

        # Remove from controllers cache
        if str(kernel.id) in self._controllers:
            del self._controllers[str(kernel.id)]
    else:
        logger.warning(f"Failed to shut down kernel {kernel.id}")

    return success
