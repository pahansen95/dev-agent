# DevAgent DDD Architecture: Project Implementation Plan

## 1. Basis for Refactor

### 1.1 What & Why

We are refactoring the DevAgent architecture to address a critical limitation: the current design does not support persistent kernel processes across CLI invocations. When a kernel is created via the `kernel create` command, the kernel process terminates when the command exits. The desired behavior is for kernels to persist indefinitely until explicitly terminated.

This refactor will implement a more robust Domain-Driven Design (DDD) architecture centered around:

1. **Event-driven communication** via a filesystem-backed event bus
2. **Explicit modeling of runtime state** as a first-class domain concept
3. **Separation of desired vs. actual state** with automatic reconciliation
4. **Cooperative multi-process architecture** without requiring daemon processes

This approach aligns with our existing architecture's core principle of treating the filesystem as the source of truth, while extending it to handle runtime process management effectively.

### 1.2 Reference Architecture Documents

The following project documents should be referenced during implementation:

1. **`docs/HierarchicalDomainDesign.md`** - The formal framework for systematically translating semantic intent into computational systems
2. **`docs/AgenticDeveloperArchitecture.md`** - The control-theoretic approach to software development
3. **`docs/AgentInterpreterArchitecture.md`** - The architectural vision for the interpreter component

These documents establish the philosophical foundation of our system:
- Files as source of truth
- Layered abstractions with well-defined gates
- Control-theoretic feedback loops for stability

## 2. DDD Architecture Details

### 2.1 Core Architectural Patterns

#### 2.1.1 Event-Sourced State Management

All state changes in the system will be mediated through domain events that:
- Represent intent (commands) and outcomes (facts)
- Are persisted to the filesystem for durability
- Enable independent observation by different components
- Support reconstruction of state from event history

#### 2.1.2 Dual-State Model

The architecture explicitly distinguishes between:
- **Desired State**: Declarative specifications of intended state (stored in metadata files)
- **Actual State**: Observable runtime behavior (running processes, actual measurements)
- **Reconciliation**: The continuous process of aligning actual with desired state

#### 2.1.3 Filesystem as Integration Layer

All components will integrate through the filesystem:
- Metadata stored as JSON in a well-defined directory structure
- Events stored as timestamped files in type-specific directories
- Consumer tracking stored as position markers for cooperative processing
- Connection files stored for process reconnection

#### 2.1.4 Cooperative Multi-Process Architecture

Processes interact without requiring a central daemon:
- Each process maintains independent consumption position
- Event polling occurs at appropriate times (startup, after operations)
- Process failures don't affect overall system integrity
- Kernel processes persist independently of creating processes

### 2.2 Bounded Contexts

The system is organized into four bounded contexts:

#### 2.2.1 Metadata Context
**Responsibility**: Manage the "desired state" of computational resources
- **Aggregates**: Session (root), Kernel
- **Repositories**: SessionRepository, KernelRepository
- **Services**: SessionService, KernelService

#### 2.2.2 Runtime Context
**Responsibility**: Manage the "actual state" of operating system processes
- **Aggregates**: KernelRuntimeState
- **Repositories**: RuntimeStateRepository
- **Services**: KernelOperator, ProcessObserver

#### 2.2.3 Event Context
**Responsibility**: Facilitate communication between bounded contexts
- **Aggregates**: EventStream (by type)
- **Repositories**: EventStore
- **Services**: EventBus, EventConsumer

#### 2.2.4 Interpreter Context
**Responsibility**: Execute computational code within kernels
- **Aggregates**: ExecutionContext
- **Repositories**: ExecutionResultRepository
- **Services**: KernelController, ExecutionService

### 2.3 Domain Model

```
┌─────────────────────────────────────────────┐
│                                             │
│              Metadata Context               │
│                                             │
│  ┌─────────┐        owns       ┌─────────┐  │
│  │ Session ├─────────────────▶ │ Kernel  │  │
│  └─────────┘                   └────┬────┘  │
│                                     │       │
└─────────────────────────────────────┼───────┘
                                      │
                   "should run as"    │
                                      ▼
┌─────────────────────────────────────────────┐
│                                             │
│              Runtime Context                │
│                                             │
│  ┌─────────────────────┐    ┌────────────┐  │
│  │ KernelRuntimeState  │◀───┤   Process  │  │
│  └─────────┬───────────┘    └────────────┘  │
│            │                                │
└────────────┼────────────────────────────────┘
             │
             │ publishes
             ▼
┌─────────────────────────────────────────────┐
│                                             │
│               Event Context                 │
│                                             │
│  ┌─────────┐  stored as  ┌────────────────┐ │
│  │ Events  ├────────────▶│ Event Streams  │ │
│  └─────────┘             └────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘
```

### 2.4 Event Flow

```
┌───────────────┐     ┌───────────────┐     ┌─────────────────┐
│ Command Side  │     │  Event Store  │     │  Query Side     │
│               │     │  (Filesystem) │     │                 │
│ publish event │────▶│ append to log │────▶│ poll for events │
└───────────────┘     └───────────────┘     └─────────────────┘
                            │                        │
                            │                        │
                            ▼                        ▼
                      ┌───────────────┐     ┌─────────────────┐
                      │   Consumer    │     │  Update View    │
                      │ Position Log  │     │    Model        │
                      └───────────────┘     └─────────────────┘
```

## 3. Gap Analysis: Current vs. Future State

### 3.1 Current State Components

| Component | Current Implementation | State |
|-----------|------------------------|-------|
| **Session & Kernel Models** | Defined in `domain/model.py` with basic lifecycle management | ✅ Exists |
| **Value Objects** | SessionId, KernelId, Reference, etc. in `domain/value_objects.py` | ✅ Exists |
| **Domain Events** | Basic events defined but not fully utilized for state transfer | ⚠️ Partial |
| **Repositories** | Interface definitions and filesystem implementations exist | ✅ Exists |
| **Process Management** | KernelController directly manages processes with parent-child relationship | ⚠️ Limited |
| **Event Bus** | Basic in-memory implementation exists, not filesystem-backed | ⚠️ Limited |
| **Operator Pattern** | Not implemented - no automatic reconciliation | ❌ Missing |
| **Runtime State Tracking** | Mixed with kernel metadata, not explicitly modeled | ❌ Missing |
| **Consumer Position Tracking** | No mechanism for multiple processes to cooperate on event stream | ❌ Missing |

### 3.2 Key Gaps to Address

1. **Event Persistence**: Current events are in-memory only, need filesystem-backed implementation
2. **Runtime State Modeling**: Need explicit domain objects for runtime state
3. **Kernel Operator**: Missing the core reconciliation engine
4. **Process Independence**: Kernel processes terminate with parent process
5. **Event Consumption Tracking**: No mechanism for cooperative event processing
6. **Reconnection Capability**: Limited ability to reconnect to existing processes

### 3.3 Leverage Points

1. **Filesystem Repository Pattern**: The existing pattern can be extended for event storage
2. **Domain Events**: Basic event structure exists and can be expanded
3. **Value Objects**: Strong typing with immutable value objects provides a foundation
4. **Repository Interfaces**: Clear abstractions enable new implementations
5. **CLI Infrastructure**: Command handling structure is in place

## 4. Implementation Milestones

### Milestone 1: Event Context Implementation (2 weeks)

**Objective**: Create the filesystem-backed event infrastructure

#### Task 1.1: Event Store Implementation

Create a filesystem-backed event store for persisting domain events:

```python
# src/DevAgent/interpreter/infrastructure/event_store.py
class FileSystemEventStore:
    """Event store that persists events to the filesystem."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.events_dir = base_dir / "events" / "streams"
        self.events_dir.mkdir(parents=True, exist_ok=True)
    
    def append(self, event: DomainEvent) -> None:
        """Append an event to its type-specific stream."""
        # Implementation details as discussed
```

#### Task 1.2: Event Consumer Tracking

Implement consumer position tracking for cooperative event processing:

```python
# src/DevAgent/interpreter/infrastructure/event_consumer.py
class EventConsumer:
    """Tracks consumption progress for a specific consumer."""
    
    def __init__(self, base_dir: Path, consumer_id: str):
        self.base_dir = base_dir
        self.consumer_id = consumer_id
        self.consumer_dir = base_dir / "events" / "consumers" / consumer_id
        self.consumer_dir.mkdir(parents=True, exist_ok=True)
    
    def get_last_position(self, event_type: str) -> float:
        """Implementation details as discussed"""
```

#### Task 1.3: Filesystem Event Bus

Create a filesystem-backed event bus implementation:

```python
# src/DevAgent/interpreter/infrastructure/fs_event_bus.py
class FileSystemEventBus:
    """Event bus implementation backed by the filesystem."""
    
    def __init__(self, base_dir: Path, consumer_id: Optional[str] = None):
        # Implementation details as discussed
```

#### Task 1.4: Enhanced Domain Events

Expand the domain events to cover runtime state changes:

```python
# src/DevAgent/interpreter/domain/events.py
@dataclass(frozen=True)
class KernelDesiredStateChanged:
    """Event raised when the desired state of a kernel changes."""
    kernel_id: KernelId
    session_id: SessionId
    previous_state: KernelStatus
    desired_state: KernelStatus
    timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelActualStateChanged:
    """Event raised when the actual state of a kernel changes."""
    # Implementation details
```

#### Task 1.5: Event Serialization/Deserialization

Implement helpers for JSON serialization/deserialization of domain events:

```python
# src/DevAgent/interpreter/infrastructure/event_serialization.py
def serialize_event(event: DomainEvent) -> Dict[str, Any]:
    """Serialize an event to a dictionary for storage."""
    # Implementation details

def deserialize_event(event_type: str, data: Dict[str, Any]) -> DomainEvent:
    """Deserialize an event from stored data."""
    # Implementation details
```

**Architectural Notes**:
- Use microsecond-precision timestamps in filenames for ordering
- Ensure atomic file writes to prevent corruption
- Consider implementing event pruning for long-running systems

### Milestone 2: Runtime Context Implementation (3 weeks)

**Objective**: Create explicit modeling of runtime state and kernel operator

#### Task 2.1: KernelStatus Enumeration

Define the possible states for a kernel:

```python
# src/DevAgent/interpreter/domain/value_objects.py
class KernelStatus(Enum):
    """Possible states for a kernel."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
```

#### Task 2.2: KernelRuntimeState Entity

Create an entity to represent the actual runtime state of a kernel:

```python
# src/DevAgent/interpreter/domain/model.py
@dataclass
class KernelRuntimeState:
    """Runtime state of a kernel process."""
    kernel_id: KernelId
    process_id: Optional[int]
    status: KernelStatus
    health_metrics: Dict[str, Any]
    last_health_check: float
    desired_status: KernelStatus
    
    def is_reconciled(self) -> bool:
        """Whether actual state matches desired state."""
        return self.status == self.desired_status
```

#### Task 2.3: RuntimeStateRepository

Create a repository interface and implementation for runtime state:

```python
# src/DevAgent/interpreter/domain/repositories.py
class RuntimeStateRepository(Protocol):
    """Repository interface for kernel runtime state."""
    # Interface definition

# src/DevAgent/interpreter/infrastructure/repositories.py
class FileSystemRuntimeStateRepository:
    """Implementation of RuntimeStateRepository using filesystem storage."""
    # Implementation details
```

#### Task 2.4: ProcessObserver

Create a service for observing actual process state:

```python
# src/DevAgent/interpreter/infrastructure/process_observer.py
class ProcessObserver:
    """Service that observes OS processes for kernels."""
    
    def observe_process(self, pid: int) -> Dict[str, Any]:
        """Observe metrics for a running process."""
        # Implementation details
    
    def is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running."""
        # Implementation details
```

#### Task 2.5: Kernel Operator

Implement the kernel operator that reconciles desired and actual state:

```python
# src/DevAgent/interpreter/infrastructure/kernel_operator.py
class KernelOperator:
    """
    Continuously reconciles desired kernel state (from filesystem) 
    with actual running kernel processes.
    """
    
    def __init__(self, base_dir: Path, event_bus: FileSystemEventBus):
        # Implementation details
    
    def start(self):
        """Start the reconciliation loop in a background thread."""
        # Implementation details
    
    def _reconcile_kernel(self, session_id: str, kernel_id: str):
        """Reconcile the state of a specific kernel."""
        # Implementation details
```

#### Task 2.6: FileSystemWatcher

Create a component to watch filesystem changes for metadata updates:

```python
# src/DevAgent/interpreter/infrastructure/fs_watcher.py
class FileSystemWatcher:
    """Watches filesystem changes in sessions and kernels."""
    # Implementation details as discussed
```

**Architectural Notes**:
- Use a background thread for the reconciliation loop, not a separate process
- Implement proper locking for shared filesystem resources
- Consider resource limits and graceful degradation
- Implement health checks and reporting

### Milestone 3: Metadata Context Refinement (2 weeks)

**Objective**: Update session and kernel models to support desired state

#### Task 3.1: Update Kernel Entity

Modify the Kernel entity to include desired state:

```python
# src/DevAgent/interpreter/domain/model.py
@dataclass
class Kernel:
    """Entity representing a computational kernel."""
    id: KernelId
    name: str
    session_id: SessionId
    kernel_type: str
    created_at: float
    last_activity: float
    desired_status: KernelStatus = KernelStatus.RUNNING
    _is_alive: bool = False
    
    def request_start(self) -> None:
        """Request that this kernel be started by the operator."""
        self.desired_status = KernelStatus.RUNNING
        self.update_last_activity()
    
    def request_shutdown(self) -> None:
        """Request that this kernel be shut down by the operator."""
        self.desired_status = KernelStatus.STOPPED
        self.update_last_activity()
```

#### Task 3.2: Update KernelFactory

Modify the KernelFactory to set appropriate initial state:

```python
# src/DevAgent/interpreter/domain/factories.py
class KernelFactory:
    """Factory for creating Kernel entities."""
    
    def create_kernel(self, session: Session, name: str, kernel_type: str = "python3") -> Kernel:
        """Create a new kernel in the given session."""
        # Updated implementation
```

#### Task 3.3: Update KernelRepository

Ensure the repository properly saves and loads the desired state:

```python
# src/DevAgent/interpreter/infrastructure/repositories.py
class FileSystemKernelRepository:
    """Implementation of KernelRepository using filesystem storage."""
    
    def save(self, kernel: Kernel) -> None:
        """Save a kernel to the repository with desired state."""
        # Updated implementation
```

#### Task 3.4: Command and Query Services

Implement command and query services for the Kernel aggregate:

```python
# src/DevAgent/interpreter/domain/services.py
class KernelCommandService:
    """Handles commands that change desired kernel state."""
    
    def request_kernel_start(self, kernel_id: KernelId) -> None:
        """Request a kernel to be started."""
        # Implementation details

class KernelQueryService:
    """Handles queries about actual kernel state."""
    
    def get_kernel_status(self, kernel_id: KernelId) -> KernelStatusDTO:
        """Get the current status of a kernel, including runtime information."""
        # Implementation details
```

**Architectural Notes**:
- Keep metadata models focused on desired state
- Use events to communicate state change intent
- Consider validation rules for state transitions
- Add meaningful error messages for invalid state changes

### Milestone 4: Interpreter Context Updates (2 weeks)

**Objective**: Update the interpreter to support persistent kernels

#### Task 4.1: Enhance KernelController

Modify the KernelController to work with the Kernel Operator:

```python
# src/DevAgent/interpreter/kernel.py
class KernelController:
    """Controls an individual kernel process."""
    
    def start_kernel(self) -> bool:
        """
        Start the kernel process.
        Updated to set metadata for the operator to handle.
        """
        # Updated implementation
    
    def execute(self, code: str) -> ExecutionResult:
        """Execute code in the kernel."""
        # Updated implementation with better reconnection logic
```

#### Task 4.2: Update ExecutionService

Modify the execution service to work with potentially reconnected kernels:

```python
# src/DevAgent/interpreter/domain/services.py
class ExecutionService:
    """Service for executing code in kernels."""
    
    def execute_code(self, kernel: Kernel, code: str) -> ExecutionResult:
        """Execute code in a kernel with improved reconnection handling."""
        # Updated implementation
```

#### Task 4.3: Enhanced Reconnection Logic

Create improved reconnection logic for existing kernel processes:

```python
# src/DevAgent/interpreter/infrastructure/kernel_adapter.py
class KernelControllerAdapter:
    """
    Adapter that connects the domain Kernel model to the infrastructure KernelController.
    """
    
    def _reconnect_to_kernel(self, kernel_id: KernelId, connection_file: Path) -> bool:
        """Attempt to reconnect to an existing kernel."""
        # Implementation details
```

#### Task 4.4: Process Detachment Implementation

Implement proper process detachment to ensure kernels persist:

```python
# src/DevAgent/interpreter/infrastructure/process_management.py
def detach_process(pid: int) -> bool:
    """Detach a process to ensure it continues after parent exits."""
    # Implementation details

def get_kernel_pid_from_connection_file(connection_file: Path) -> Optional[int]:
    """Extract PID from connection file if available."""
    # Implementation details
```

**Architectural Notes**:
- Use Jupyter's existing connection file mechanism for reconnection
- Consider platform-specific process management details
- Implement reconnection testing for robustness
- Handle graceful timeouts for unresponsive kernels

### Milestone 5: CLI Integration (1 week)

**Objective**: Update CLI to work with the enhanced architecture

#### Task 5.1: Update CLI Handlers

Modify CLI command handlers to interact with the event bus:

```python
# src/DevAgent/__main__.py
def handle_interpreter_kernel_create(args: argparse.Namespace) -> bool:
    """Handle the interpreter kernel create command with event processing."""
    # Updated implementation
```

#### Task 5.2: Add Event Processing to CLI

Ensure CLI commands process events appropriately:

```python
# src/DevAgent/__main__.py
class CLI:
    @classmethod
    @contextlib.contextmanager
    def session(cls):
        """Enhanced session with event processing."""
        # Updated implementation
```

#### Task 5.3: Add Status Command

Create a new command to display kernel status:

```python
# src/DevAgent/__main__.py
def handle_interpreter_kernel_status(args: argparse.Namespace) -> bool:
    """Handle the interpreter kernel status command."""
    # Implementation details
```

#### Task 5.4: Update Command Help Documentation

Update CLI help documentation to describe new behavior:

```python
# src/DevAgent/__main__.py
def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up the argument parser with updated documentation."""
    # Updated implementation
```

**Architectural Notes**:
- Ensure CLI commands work when operator is not running
- Add clear error messages for connection failures
- Consider adding verbose output option for debugging
- Make status command formatting user-friendly

### Milestone 6: Testing and Documentation (2 weeks)

**Objective**: Ensure the refactored system is well-tested and documented

#### Task 6.1: Unit Tests for New Components

Create comprehensive unit tests for new components:

```python
# tests/unit/interpreter/infrastructure/test_fs_event_bus.py
# tests/unit/interpreter/infrastructure/test_kernel_operator.py
# tests/unit/interpreter/domain/test_kernel_runtime_state.py
```

#### Task 6.2: Integration Tests

Create integration tests for the complete system:

```python
# tests/integration/interpreter/test_persistence.py
class KernelPersistenceTests(unittest.TestCase):
    """Test that kernels persist across process restarts."""
    # Implementation details
```

#### Task 6.3: Update Architecture Documentation

Update architecture documentation to reflect the new design:

```markdown
# docs/EventSourcedInterpreter.md
# Event-Sourced Interpreter Architecture

This document describes the event-sourced architecture of the DevAgent Interpreter...
```

#### Task 6.4: CLI Documentation Updates

Update CLI documentation to explain the new kernel persistence behavior:

```markdown
# docs/cli.md
## Kernel Commands

Kernels now persist beyond the lifetime of the CLI command that created them...
```

**Architectural Notes**:
- Create tests that verify process independence
- Document edge cases and recovery procedures
- Include diagrams to illustrate the architecture
- Add examples of common usage patterns

## 5. Additional References and Context

### 5.1 Design Patterns Referenced

1. **Event Sourcing** - Martin Fowler: https://martinfowler.com/eaaDev/EventSourcing.html
2. **Command Query Responsibility Segregation (CQRS)** - Martin Fowler: https://martinfowler.com/bliki/CQRS.html
3. **Operator Pattern** - Kubernetes: https://kubernetes.io/docs/concepts/extend-kubernetes/operator/
4. **Anti-Corruption Layer** - Eric Evans: Domain-Driven Design (book)
5. **Repository Pattern** - Eric Evans: Domain-Driven Design (book)

### 5.2 Relevant External Resources

1. **Jupyter Kernel Management**: https://jupyter-client.readthedocs.io/en/stable/kernels.html
2. **Process Management in Python**: https://docs.python.org/3/library/subprocess.html
3. **Filesystem Monitoring**: https://pythonhosted.org/watchdog/

### 5.3 Future Considerations

1. **Resource Limits**: Implement policy-based limits on resource consumption
2. **Auto-Shutdown**: Add automatic shutdown for inactive kernels
3. **Web Interface**: Consider adding a web interface for kernel management
4. **Distributed Operation**: Support for multiple machines in a cluster
5. **Plugin Architecture**: Enable custom event handlers and reconcilers

### 5.4 Implementation Priorities

1. **Correctness**: Ensure the system correctly maintains kernel state
2. **Resilience**: Make the system recover gracefully from failures
3. **Performance**: Optimize filesystem operations for scale
4. **Usability**: Provide clear feedback and status information
5. **Extensibility**: Make the architecture easy to extend