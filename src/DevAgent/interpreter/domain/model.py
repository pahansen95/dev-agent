from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Set
from .value_objects import SessionId, KernelId, ExecutionResult
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