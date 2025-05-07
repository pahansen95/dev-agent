"""
DevAgent Interpreter Architecture

This module defines the architecture for DevAgent's interpreter system, which provides
computational environments for agents through a managed Jupyter infrastructure.

# Usage & Capabilities

An Execution Environment is the single point of integration into the Development
Environment for both human developers, development agents & standard automations.
The Execution Environment provides a realtime, programmatic way to interact with
a project such as for:

- Query & Search
- File Manipulation
- Git & Source Control
- Tests & Debugging
- Documentation

The Execution Environment does not allow for arbitrary code execution; every connecting
entity must first authenticate themselves to gain access to a session of certain
permissions. Permissions may never be elevated during the lifetime of a session.

# Architectural Overview

The interpreter system is designed with clean separation of concerns, dividing
responsibilities into four main components with well-defined boundaries:

1. **ServerController**: Infrastructure layer - Manages the lifecycle of the Jupyter Server
   process, providing connection information to other components when requested.

2. **StateManager**: Persistence layer - Handles on-disk storage of session configurations,
   kernel registry, and filesystem space, ensuring sessions survive server restarts.

3. **KernelController**: Runtime layer - Manages kernels within a session, handling
   kernel lifecycle operations through the Jupyter Server API.

4. **SessionManager**: Application layer - Coordinates between state persistence and 
   kernel operations, providing a unified interface for session management. Uses but
   does not control server infrastructure.

# Conceptual Model

In DevAgent, an Interpreter Session represents a persistent computational environment
that can be accessed by multiple consumers (agents, humans, or automated systems).
Similar to tmux sessions, these environments provide isolated execution contexts
that maintain state across connections and server restarts.

## Key Concepts

1. **Session**: A named, persistent environment with its own filesystem space and
   kernel(s). Sessions are project-owned resources that multiple consumers can
   attach to. They persist indefinitely until explicitly purged.

2. **Kernel**: A computational engine within a session. Initially, each session has
   a single "main" kernel, but the architecture supports multiple specialized kernels
   per session. Kernels maintain their own execution state.

3. **Session Filesystem**: Each session has a dedicated filesystem area for temporary
   files, outputs, and working data. This provides isolation between different
   session contexts.

## Lifecycle States

**Kernel Lifecycle**:
- Non-existent → Configured → Starting → Running → Busy/Idle → Stopping → Stopped

**Session Lifecycle**:
- Non-existent → Created → Active/Inactive → Purged

# Component Relationships & Dependencies

- **SessionManager** uses connection provider to get server connection details
- **SessionManager** uses **StateManager** to persist interpreter state
- **SessionManager** creates and manages **KernelController** instances
- **KernelController** uses the Jupyter Server API to interact with kernels
- **KernelController** notifies **SessionManager** of state changes
- **ServerController** is independent and manages only the server process

## Component Interaction

The components interact through well-defined interfaces and dependencies:

```
┌─────────────────┐         ┌─────────────────┐
│                 │         │                 │
│ ServerController│◄────────┤ SessionManager  │
│                 │connection│                 │
└────────┬────────┘ provider└───────┬─────────┘
         │                          │
         │                    ┌─────┴─────┐
         │                    │           │
         │                    ▼           ▼
         │           ┌─────────────┐ ┌────────────┐
         │           │             │ │            │
         └──────────►│ Jupyter API │ │StateManager│
                     │             │ │            │
                     └──────┬──────┘ └────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │                 │
                  │KernelController │
                  │                 │
                  └─────────────────┘
```

# Data Flow

1. **SessionManager** is the primary point of entry for session operations
2. For kernel operations, it delegates to the appropriate **KernelController**
3. **KernelController** performs operations via Jupyter Server API
4. State changes are propagated back to **SessionManager**
5. **SessionManager** uses **StateManager** to persist changes

# State Structure

Sessions are persisted as directories with a standard structure:

```
session-NAME/               # Base directory for a session
├── metadata.json           # Session metadata (creation time, etc.)
├── kernels.json            # Registry of kernels in this session
└── fs/                     # Session filesystem (working directory)
```

# Usage Examples

```python
# Create infrastructure components
server_controller = ServerController("/path/to/server_dir") 
state_manager = StateManager("/path/to/state_dir")

# Get connection provider function
def get_connection():
    return server_controller.get_connection_info()

# Create application component with dependencies
session_manager = SessionManager(
    state_manager=state_manager,
    connection_provider=get_connection
)

# Start server (separately from session management)
server_controller.up()

# Create and use a session
session_manager.create_session("dev_session")
stdout, stderr = session_manager.execute("dev_session", "main", "print('Hello world')")

# Clean up
server_controller.down()
```

This architecture ensures:
- Clear separation of responsibilities
- Explicit dependencies
- Centralized state management
- Clean interfaces between components
- Independence between infrastructure and application concerns
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path

from .server import ServerController
from .session import StateManager, KernelController, SessionManager

__all__ = ['ServerController', 'StateManager', 'KernelController', 'SessionManager']
