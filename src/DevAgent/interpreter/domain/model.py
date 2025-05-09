from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Set, Any
from .value_objects import SessionId, KernelId, ExecutionResult, KernelStatus
from .exceptions import KernelNotFoundError, KernelAlreadyExistsError

@dataclass
class Kernel:
    """Entity representing a computational kernel."""
    id: KernelId
    name: str
    session_id: SessionId
    kernel_type: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    desired_status: KernelStatus = KernelStatus.RUNNING
    _is_alive: bool = False
    
    def start(self) -> bool:
        """
        Start the kernel process.
        
        This is a domain method that will be implemented by infrastructure.
        Returns True if the kernel was successfully started.
        """
        # This is a placeholder - will be implemented by infrastructure adapter
        pass
    
    def execute(self, code: str) -> ExecutionResult:
        """
        Execute code in this kernel.
        
        This is a domain method that will be implemented by infrastructure.
        Returns the result of code execution.
        """
        # This is a placeholder - will be implemented by infrastructure adapter
        pass
    
    def interrupt(self) -> bool:
        """
        Interrupt the kernel's execution.
        
        This is a domain method that will be implemented by infrastructure.
        Returns True if the kernel was successfully interrupted.
        """
        # This is a placeholder - will be implemented by infrastructure adapter
        pass
    
    def restart(self) -> bool:
        """
        Restart the kernel process.
        
        This is a domain method that will be implemented by infrastructure.
        Returns True if the kernel was successfully restarted.
        """
        # This is a placeholder - will be implemented by infrastructure adapter
        pass
    
    def shutdown(self) -> bool:
        """
        Shutdown the kernel process.
        
        This is a domain method that will be implemented by infrastructure.
        Returns True if the kernel was successfully shut down.
        """
        # This is a placeholder - will be implemented by infrastructure adapter
        pass
    
    @property
    def is_alive(self) -> bool:
        """Check if the kernel is alive."""
        return self._is_alive

    def update_last_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = time.time()

    def request_start(self) -> None:
        """Request that this kernel be started by the operator."""
        self.desired_status = KernelStatus.RUNNING
        self.update_last_activity()

    def request_shutdown(self) -> None:
        """Request that this kernel be shut down by the operator."""
        self.desired_status = KernelStatus.STOPPED
        self.update_last_activity()

@dataclass
class Session:
    """Aggregate root representing a computational session."""
    id: SessionId
    name: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    _kernels: Dict[str, Kernel] = field(default_factory=dict)
    
    def add_kernel(self, kernel: Kernel) -> None:
        """Add a kernel to this session."""
        if str(kernel.id) in self._kernels:
            raise KernelAlreadyExistsError(f"Kernel with ID {kernel.id} already exists in session")
        self._kernels[str(kernel.id)] = kernel
        self.update_last_activity()
    
    def get_kernel(self, kernel_id: KernelId) -> Kernel:
        """Get a kernel by ID."""
        kernel = self._kernels.get(str(kernel_id))
        if not kernel:
            raise KernelNotFoundError(f"Kernel {kernel_id} not found in session {self.id}")
        return kernel
    
    def get_kernel_by_name(self, name: str) -> Optional[Kernel]:
        """Get a kernel by name."""
        for kernel in self._kernels.values():
            if kernel.name == name:
                return kernel
        return None
    
    def list_kernels(self) -> List[Kernel]:
        """List all kernels in this session."""
        return list(self._kernels.values())
    
    def remove_kernel(self, kernel_id: KernelId) -> None:
        """Remove a kernel from this session."""
        if str(kernel_id) in self._kernels:
            del self._kernels[str(kernel_id)]
            self.update_last_activity()
        else:
            raise KernelNotFoundError(f"Kernel {kernel_id} not found in session {self.id}")
    
    def update_last_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = time.time()
    
    def has_kernel_with_name(self, name: str) -> bool:
        """Check if the session has a kernel with the given name."""
        return any(kernel.name == name for kernel in self._kernels.values())

@dataclass
class KernelRuntimeState:
    """Entity representing the runtime state of a kernel process."""
    kernel_id: KernelId
    session_id: SessionId
    status: KernelStatus = KernelStatus.STOPPED
    desired_status: KernelStatus = KernelStatus.STOPPED
    process_id: Optional[int] = None
    connection_file: Optional[str] = None
    jupyter_kernel_id: Optional[str] = None
    health_metrics: Dict[str, Any] = field(default_factory=dict)
    last_health_check: float = field(default_factory=time.time)
    last_reconciliation: float = field(default_factory=time.time)

    def is_reconciled(self) -> bool:
        """
        Check if the actual state matches the desired state.

        Returns:
            True if the actual state matches the desired state
        """
        return self.status == self.desired_status

    def needs_reconciliation(self, threshold_seconds: float = 30.0) -> bool:
        """
        Check if the state needs reconciliation based on time since last reconciliation.

        Args:
            threshold_seconds: Time threshold in seconds

        Returns:
            True if reconciliation is needed
        """
        if not self.is_reconciled():
            return True

        time_since_reconciliation = time.time() - self.last_reconciliation
        return time_since_reconciliation > threshold_seconds

    def update_status(self, new_status: KernelStatus) -> None:
        """
        Update the actual status of the kernel.

        Args:
            new_status: The new status
        """
        self.status = new_status

    def update_desired_status(self, desired_status: KernelStatus) -> None:
        """
        Update the desired status of the kernel.

        Args:
            desired_status: The new desired status
        """
        self.desired_status = desired_status

    def update_process_info(self, process_id: Optional[int], connection_file: Optional[str], jupyter_kernel_id: Optional[str] = None) -> None:
        """
        Update the process information.

        Args:
            process_id: The process ID
            connection_file: Path to the connection file
            jupyter_kernel_id: The Jupyter kernel ID
        """
        self.process_id = process_id
        self.connection_file = connection_file
        if jupyter_kernel_id:
            self.jupyter_kernel_id = jupyter_kernel_id

    def update_health_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Update the health metrics for the kernel.

        Args:
            metrics: Health metrics data
        """
        self.health_metrics = metrics
        self.last_health_check = time.time()

    def mark_as_reconciled(self) -> None:
        """Mark the state as reconciled at the current time."""
        self.last_reconciliation = time.time()

    def is_process_running(self) -> bool:
        """
        Check if the process is believed to be running based on status.

        Returns:
            True if the process is expected to be running
        """
        return self.status in {KernelStatus.RUNNING, KernelStatus.STARTING}

    def should_start_process(self) -> bool:
        """
        Check if the process should be started to reach desired state.

        Returns:
            True if the process should be started
        """
        return (
            self.desired_status == KernelStatus.RUNNING and
            self.status in {KernelStatus.STOPPED, KernelStatus.FAILED}
        )

    def should_stop_process(self) -> bool:
        """
        Check if the process should be stopped to reach desired state.

        Returns:
            True if the process should be stopped
        """
        return (
            self.desired_status == KernelStatus.STOPPED and
            self.status in {KernelStatus.RUNNING, KernelStatus.STARTING}
        )