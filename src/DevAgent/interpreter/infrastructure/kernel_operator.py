import time
import logging
import threading
import queue
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple

from ..domain.model import KernelRuntimeState
from ..domain.value_objects import KernelId, SessionId, KernelStatus
from ..domain.events import (
    KernelActualStateChanged, KernelDesiredStateChanged, 
    KernelStateReconciled, KernelHealthChecked,
    KernelProcessStarted, KernelProcessExited, KernelProcessDetached
)
from ..domain.repositories import RuntimeStateRepository, KernelRepository
from .fs_event_bus import FileSystemEventBus
from .process_observer import ProcessObserver
from .kernel_adapter import KernelControllerAdapter

logger = logging.getLogger(__name__)

class KernelOperator:
    """
    Continuously reconciles desired kernel state with actual running kernel processes.
    """
    
    def __init__(
        self, 
        base_dir: Path, 
        event_bus: FileSystemEventBus,
        runtime_repo: RuntimeStateRepository,
        kernel_repo: KernelRepository,
        polling_interval: float = 5.0
    ):
        """
        Initialize the kernel operator.
        
        Args:
            base_dir: Base directory for all interpreter files
            event_bus: Event bus for publishing events
            runtime_repo: Repository for kernel runtime state
            kernel_repo: Repository for kernel metadata
            polling_interval: How often to check for state changes (seconds)
        """
        self.base_dir = base_dir
        self.event_bus = event_bus
        self.runtime_repo = runtime_repo
        self.kernel_repo = kernel_repo
        self.process_observer = ProcessObserver()
        self.kernel_adapter = KernelControllerAdapter(base_dir)
        self.polling_interval = polling_interval
        
        self._stopping = False
        self._reconcile_thread = None
        self._health_check_thread = None
        self._event_thread = None
        self._task_queue = queue.Queue()
        
        # Subscribe to events
        self.event_bus.subscribe(KernelDesiredStateChanged, self._handle_desired_state_changed)
        self.event_bus.subscribe(KernelActualStateChanged, self._handle_actual_state_changed)
    
    def start(self) -> None:
        """Start the reconciliation loop and related threads."""
        if self._reconcile_thread and self._reconcile_thread.is_alive():
            logger.warning("Kernel operator already running")
            return
        
        logger.info("Starting kernel operator")
        self._stopping = False
        
        # Start reconciliation thread
        self._reconcile_thread = threading.Thread(
            target=self._reconciliation_loop,
            name="kernel-operator-reconcile",
            daemon=True
        )
        self._reconcile_thread.start()
        
        # Start health check thread
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            name="kernel-operator-health",
            daemon=True
        )
        self._health_check_thread.start()
        
        # Start event processing thread
        self._event_thread = threading.Thread(
            target=self._event_loop,
            name="kernel-operator-events",
            daemon=True
        )
        self._event_thread.start()
    
    def stop(self) -> None:
        """Stop the reconciliation loop and related threads."""
        logger.info("Stopping kernel operator")
        self._stopping = True
        
        # Wait for threads to finish
        if self._reconcile_thread:
            self._reconcile_thread.join(timeout=2.0)
        if self._health_check_thread:
            self._health_check_thread.join(timeout=2.0)
        if self._event_thread:
            self._event_thread.join(timeout=2.0)
        
        logger.info("Kernel operator stopped")
    
    def queue_reconciliation(self, kernel_id: KernelId) -> None:
        """
        Queue a specific kernel for immediate reconciliation.
        
        Args:
            kernel_id: The ID of the kernel to reconcile
        """
        self._task_queue.put(("reconcile", str(kernel_id)))
    
    def queue_health_check(self, kernel_id: KernelId) -> None:
        """
        Queue a specific kernel for immediate health check.
        
        Args:
            kernel_id: The ID of the kernel to check
        """
        self._task_queue.put(("health_check", str(kernel_id)))
    
    def _reconciliation_loop(self) -> None:
        """Main loop that reconciles kernel states continuously."""
        logger.info("Starting reconciliation loop")
        
        while not self._stopping:
            try:
                # Get all runtime states that need reconciliation
                runtime_states = self.runtime_repo.list_all()
                for state in runtime_states:
                    if state.needs_reconciliation():
                        self._reconcile_kernel(state.kernel_id, state.session_id)
                
                # Sleep between iterations
                time.sleep(self.polling_interval)
            
            except Exception as e:
                logger.error(f"Error in reconciliation loop: {e}")
                time.sleep(1.0)  # Shorter sleep on error
    
    def _health_check_loop(self) -> None:
        """Loop that performs health checks on running kernels."""
        logger.info("Starting health check loop")
        
        while not self._stopping:
            try:
                # Get all active runtime states
                active_states = self.runtime_repo.list_active()
                for state in active_states:
                    if state.process_id:
                        self._check_kernel_health(state.kernel_id, state.session_id, state.process_id)
                
                # Sleep between iterations (longer than reconciliation)
                time.sleep(self.polling_interval * 2)
            
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1.0)  # Shorter sleep on error
    
    def _event_loop(self) -> None:
        """Loop that processes events from the event bus."""
        logger.info("Starting event polling loop")
        
        while not self._stopping:
            try:
                # Process any pending tasks in the queue
                try:
                    task_type, kernel_id_str = self._task_queue.get(block=False)
                    kernel_id = KernelId(kernel_id_str)
                    
                    # Find the runtime state
                    state = self.runtime_repo.find_by_kernel_id(kernel_id)
                    if state:
                        if task_type == "reconcile":
                            self._reconcile_kernel(kernel_id, state.session_id)
                        elif task_type == "health_check" and state.process_id:
                            self._check_kernel_health(kernel_id, state.session_id, state.process_id)
                    
                    self._task_queue.task_done()
                except queue.Empty:
                    pass
                
                # Poll for new events
                self.event_bus.poll_events()
                
                # Sleep briefly
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in event loop: {e}")
                time.sleep(1.0)  # Longer sleep on error
    
    def _handle_desired_state_changed(self, event: KernelDesiredStateChanged) -> None:
        """
        Handle desired state changed events.
        
        Args:
            event: The event to handle
        """
        logger.debug(f"Handling desired state change for kernel {event.kernel_id}: {event.desired_state}")
        
        # Queue immediate reconciliation
        self.queue_reconciliation(event.kernel_id)
    
    def _handle_actual_state_changed(self, event: KernelActualStateChanged) -> None:
        """
        Handle actual state changed events.
        
        Args:
            event: The event to handle
        """
        logger.debug(f"Handling actual state change for kernel {event.kernel_id}: {event.actual_state}")
        
        # Queue immediate reconciliation
        self.queue_reconciliation(event.kernel_id)
    
    def _reconcile_kernel(self, kernel_id: KernelId, session_id: SessionId) -> None:
        """
        Reconcile the state of a specific kernel.
        
        Args:
            kernel_id: The kernel ID
            session_id: The session ID
        """
        logger.debug(f"Reconciling kernel {kernel_id}")
        
        # Get runtime state and kernel metadata
        runtime_state = self.runtime_repo.find_by_kernel_id(kernel_id)
        kernel = self.kernel_repo.find_by_id(kernel_id)
        
        if not runtime_state or not kernel:
            logger.warning(f"Cannot reconcile kernel {kernel_id}: Missing runtime state or kernel metadata")
            return
        
        # Update runtime state with kernel's desired status (if different)
        if runtime_state.desired_status != kernel.desired_status:
            runtime_state.update_desired_status(kernel.desired_status)
            self.runtime_repo.save(runtime_state)
        
        # Check actual state vs desired state
        if runtime_state.is_reconciled():
            logger.debug(f"Kernel {kernel_id} is already reconciled: {runtime_state.status}")
            runtime_state.mark_as_reconciled()
            self.runtime_repo.save(runtime_state)
            return
        
        # Handle different reconciliation scenarios
        if runtime_state.should_start_process():
            self._start_kernel_process(runtime_state)
        elif runtime_state.should_stop_process():
            self._stop_kernel_process(runtime_state)
        else:
            # Check if process is still running when it should be
            if runtime_state.status == KernelStatus.RUNNING and runtime_state.process_id:
                if not self.process_observer.is_process_running(runtime_state.process_id):
                    # Process died unexpectedly
                    logger.warning(f"Kernel {kernel_id} process {runtime_state.process_id} died unexpectedly")
                    
                    # Update status
                    previous_status = runtime_state.status
                    runtime_state.update_status(KernelStatus.FAILED)
                    self.runtime_repo.save(runtime_state)
                    
                    # Publish event
                    self.event_bus.publish(KernelProcessExited(
                        kernel_id=kernel_id,
                        session_id=session_id,
                        process_id=runtime_state.process_id,
                        exit_code=None,
                        error_message="Process died unexpectedly",
                        timestamp=time.time()
                    ))
                    
                    # If desired state is RUNNING, queue another reconciliation to restart
                    if runtime_state.desired_status == KernelStatus.RUNNING:
                        self.queue_reconciliation(kernel_id)
    
    def _start_kernel_process(self, runtime_state: KernelRuntimeState) -> None:
        """
        Start a kernel process.
        
        Args:
            runtime_state: The runtime state to update
        """
        kernel_id = runtime_state.kernel_id
        session_id = runtime_state.session_id
        
        logger.info(f"Starting kernel process for {kernel_id}")
        
        # Update status to starting
        previous_status = runtime_state.status
        runtime_state.update_status(KernelStatus.STARTING)
        self.runtime_repo.save(runtime_state)
        
        # Get kernel metadata
        kernel = self.kernel_repo.find_by_id(kernel_id)
        if not kernel:
            logger.error(f"Cannot start kernel {kernel_id}: Kernel metadata not found")
            runtime_state.update_status(KernelStatus.FAILED)
            self.runtime_repo.save(runtime_state)
            return
        
        try:
            # Create kernel controller and start kernel
            controller = self.kernel_adapter.create_controller(
                kernel_id=str(kernel_id),
                name=kernel.name,
                kernel_type=kernel.kernel_type,
                session_id=str(session_id),
                workspace_dir=self.base_dir / "runtime" / "workspaces" / str(kernel_id)
            )
            
            # Start the kernel process
            if controller.start_kernel():
                # Get process ID and connection file
                process_id = None
                if controller.connection_file:
                    # Try to get PID from connection file
                    process_id = self.process_observer.get_kernel_pid_from_connection_file(controller.connection_file)
                
                if process_id:
                    # Update runtime state with process info
                    runtime_state.update_process_info(
                        process_id=process_id,
                        connection_file=controller.connection_file,
                        jupyter_kernel_id=controller.jupyter_kernel_id
                    )
                    runtime_state.update_status(KernelStatus.RUNNING)
                    runtime_state.mark_as_reconciled()
                    self.runtime_repo.save(runtime_state)
                    
                    # Publish events
                    self.event_bus.publish(KernelProcessStarted(
                        kernel_id=kernel_id,
                        session_id=session_id,
                        process_id=process_id,
                        connection_file=controller.connection_file,
                        jupyter_kernel_id=controller.jupyter_kernel_id,
                        timestamp=time.time()
                    ))
                    
                    self.event_bus.publish(KernelStateReconciled(
                        kernel_id=kernel_id,
                        session_id=session_id,
                        state=KernelStatus.RUNNING,
                        process_id=process_id,
                        connection_file=controller.connection_file,
                        timestamp=time.time()
                    ))
                    
                    # Detach process to ensure it persists
                    if self.process_observer.detach_process(process_id):
                        self.event_bus.publish(KernelProcessDetached(
                            kernel_id=kernel_id,
                            session_id=session_id,
                            process_id=process_id,
                            timestamp=time.time()
                        ))
                    
                    # Queue a health check
                    self.queue_health_check(kernel_id)
                else:
                    # No process ID found
                    logger.warning(f"Started kernel {kernel_id} but could not determine process ID")
                    runtime_state.update_process_info(
                        process_id=None,
                        connection_file=controller.connection_file,
                        jupyter_kernel_id=controller.jupyter_kernel_id
                    )
                    runtime_state.update_status(KernelStatus.RUNNING)  # Assume it's running anyway
                    runtime_state.mark_as_reconciled()
                    self.runtime_repo.save(runtime_state)
                    
                    # Publish event
                    self.event_bus.publish(KernelStateReconciled(
                        kernel_id=kernel_id,
                        session_id=session_id,
                        state=KernelStatus.RUNNING,
                        process_id=None,
                        connection_file=controller.connection_file,
                        timestamp=time.time()
                    ))
            else:
                # Failed to start kernel
                logger.error(f"Failed to start kernel {kernel_id}")
                runtime_state.update_status(KernelStatus.FAILED)
                self.runtime_repo.save(runtime_state)
        
        except Exception as e:
            logger.error(f"Error starting kernel {kernel_id}: {e}")
            runtime_state.update_status(KernelStatus.FAILED)
            self.runtime_repo.save(runtime_state)
    
    def _stop_kernel_process(self, runtime_state: KernelRuntimeState) -> None:
        """
        Stop a kernel process.
        
        Args:
            runtime_state: The runtime state to update
        """
        kernel_id = runtime_state.kernel_id
        session_id = runtime_state.session_id
        process_id = runtime_state.process_id
        
        if not process_id:
            logger.warning(f"Cannot stop kernel {kernel_id}: No process ID")
            runtime_state.update_status(KernelStatus.STOPPED)
            runtime_state.mark_as_reconciled()
            self.runtime_repo.save(runtime_state)
            return
        
        logger.info(f"Stopping kernel process {process_id} for {kernel_id}")
        
        # Update status to stopping
        previous_status = runtime_state.status
        runtime_state.update_status(KernelStatus.STOPPING)
        self.runtime_repo.save(runtime_state)
        
        try:
            # Check if process is still running
            if self.process_observer.is_process_running(process_id):
                # Try to create controller and shut down gracefully
                if runtime_state.connection_file:
                    try:
                        controller = self.kernel_adapter.reconnect_controller(
                            kernel_id=str(kernel_id),
                            connection_file=runtime_state.connection_file
                        )
                        
                        if controller:
                            # Try graceful shutdown
                            if controller.shutdown():
                                logger.debug(f"Gracefully shut down kernel {kernel_id}")
                    except Exception as e:
                        logger.error(f"Error reconnecting to kernel {kernel_id}: {e}")
                
                # Check if process is still running after graceful shutdown attempt
                if self.process_observer.is_process_running(process_id):
                    # Try to terminate the process
                    try:
                        import signal
                        import os
                        
                        # Send SIGTERM
                        os.kill(process_id, signal.SIGTERM)
                        
                        # Wait a bit for process to terminate
                        max_wait = 5
                        for _ in range(max_wait * 10):
                            if not self.process_observer.is_process_running(process_id):
                                break
                            time.sleep(0.1)
                        
                        # If still running, send SIGKILL
                        if self.process_observer.is_process_running(process_id):
                            logger.warning(f"Kernel {kernel_id} not responding to SIGTERM, sending SIGKILL")
                            os.kill(process_id, signal.SIGKILL)
                    except Exception as e:
                        logger.error(f"Error terminating kernel {kernel_id} process: {e}")
            
            # Check final process state
            if not self.process_observer.is_process_running(process_id):
                # Process stopped successfully
                logger.info(f"Kernel {kernel_id} process {process_id} stopped")
                
                # Get exit code if possible
                exit_code = self.process_observer.get_process_exit_code(process_id)
                
                # Update runtime state
                runtime_state.update_status(KernelStatus.STOPPED)
                runtime_state.update_process_info(None, None, None)
                runtime_state.mark_as_reconciled()
                self.runtime_repo.save(runtime_state)
                
                # Publish events
                self.event_bus.publish(KernelProcessExited(
                    kernel_id=kernel_id,
                    session_id=session_id,
                    process_id=process_id,
                    exit_code=exit_code,
                    timestamp=time.time()
                ))
                
                self.event_bus.publish(KernelStateReconciled(
                    kernel_id=kernel_id,
                    session_id=session_id,
                    state=KernelStatus.STOPPED,
                    timestamp=time.time()
                ))
            else:
                # Process still running
                logger.warning(f"Kernel {kernel_id} process {process_id} could not be stopped")
                runtime_state.update_status(KernelStatus.FAILED)
                self.runtime_repo.save(runtime_state)
        
        except Exception as e:
            logger.error(f"Error stopping kernel {kernel_id}: {e}")
            runtime_state.update_status(KernelStatus.FAILED)
            self.runtime_repo.save(runtime_state)
    
    def _check_kernel_health(self, kernel_id: KernelId, session_id: SessionId, process_id: int) -> None:
        """
        Check the health of a kernel process.
        
        Args:
            kernel_id: The kernel ID
            session_id: The session ID
            process_id: The process ID
        """
        logger.debug(f"Checking health of kernel {kernel_id} process {process_id}")
        
        # Get runtime state
        runtime_state = self.runtime_repo.find_by_kernel_id(kernel_id)
        if not runtime_state:
            logger.warning(f"Cannot check health of kernel {kernel_id}: Runtime state not found")
            return
        
        # Get process metrics
        metrics = self.process_observer.observe_process(process_id)
        
        # Check if process is running
        is_healthy = metrics.get("running", False)
        
        # Update runtime state
        runtime_state.update_health_metrics(metrics)
        
        # If process is not running but status is RUNNING, queue reconciliation
        if not is_healthy and runtime_state.status == KernelStatus.RUNNING:
            logger.warning(f"Kernel {kernel_id} process {process_id} is not running, queuing reconciliation")
            self.queue_reconciliation(kernel_id)
        
        self.runtime_repo.save(runtime_state)
        
        # Publish event
        self.event_bus.publish(KernelHealthChecked(
            kernel_id=kernel_id,
            session_id=session_id,
            is_healthy=is_healthy,
            metrics=metrics,
            process_id=process_id,
            timestamp=time.time()
        ))