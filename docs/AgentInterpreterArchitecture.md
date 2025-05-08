# DevAgent Interpreter Architecture

**Document Version:** 2.0  
**Status:** Draft  
**Last Updated:** May 8, 2025  

## 1. Executive Summary

The DevAgent Interpreter is the foundational computational bridge enabling development agents to interact with, understand, and manipulate software projects. This architecture defines a persistent, project-centric execution environment based on direct kernel integration, providing a bidirectional interface between agent intelligence and project reality.

The system creates a seamless integration layer where tools become programmable interfaces, computation becomes interactive, and development becomes automated. By adopting a filesystem-first approach with a dual-naming system, the architecture delivers a robust, intuitive platform for autonomous development workflows.

## 2. System Context

### 2.1 Purpose

The DevAgent Interpreter serves as:

- A **control surface** for manipulating project artifacts
- A **visibility window** into project state and structure
- An **integration nexus** for diverse development tools
- A **computational fabric** for dynamic code execution
- A **programmable interface** for development automation

### 2.2 Scope Boundaries

The Interpreter system encompasses:

- Session lifecycle management
- Kernel process control
- Code execution and result handling
- Tool interface abstraction
- State persistence mechanisms

The system explicitly does not include:

- Agent reasoning or decision-making components
- User interface elements
- Source control implementation (though it provides interfaces to it)
- Build system implementation (though it provides interfaces to it)

## 3. Architectural Principles

1. **Filesystem as Source of Truth**
   - All persistent state lives in filesystem structures
   - Memory is just a cache of the filesystem
   - Directory structure reflects computational organization

2. **Dual-Reference System**
   - Human-meaningful names via symlinks
   - System-assigned unique IDs for robustness
   - Transparent resolution between names and IDs

3. **Direct Kernel Integration**
   - Direct communication with Jupyter kernels
   - No Jupyter Server dependency
   - Full kernel lifecycle management

4. **Session-Based Workspaces**
   - Sessions group related computational contexts
   - Sessions maintain isolation from one another
   - Sessions persist across process restarts

5. **Controlled State Persistence**
   - State changes are atomic and durable
   - Recovery from interruption is automatic
   - Resource lifecycle is explicitly managed

6. **Project Centricity**
   - The project is the primary subject of all operations
   - Session filesystem is aligned with project structure
   - Computation occurs in the context of project artifacts

## 4. System Architecture

### 4.1 Component Overview

The Interpreter architecture consists of the following primary components:

```
┌────────────────────┐
│  InterpreterAPI    │
└──────────┬─────────┘
           │
┌──────────▼─────────┐
│   SessionManager   │
└──────────┬─────────┘
           │
┌──────────▼─────────┐
│NamedResourceManager│◄───┐
└──────────┬─────────┘    │
           │              │
    ┌──────▼────────┐     │
    │ KernelRegistry │     │
    └──────┬─────────┘     │
           │               │
┌──────────▼─────────┐    │
│     Session        │────┘
└──────────┬─────────┘
           │
┌──────────▼─────────┐
│  KernelController  │
└──────────┬─────────┘
           │
┌──────────▼─────────┐
│  jupyter_client    │
└────────────────────┘
```

### 4.2 Key Components

#### 4.2.1 InterpreterAPI

The public interface for interacting with the Interpreter system:
- Creates and manages sessions and kernels
- Executes code in specified kernels
- Provides operations for session/kernel lifecycle

#### 4.2.2 SessionManager

Orchestrates the lifecycle of interpreter sessions:
- Creates and retrieves sessions with human-friendly names
- Manages session state persistence
- Coordinates between NamedResourceManager and Sessions

#### 4.2.3 NamedResourceManager

Handles the mapping between human-readable names and system IDs:
- Maintains registry of name-to-ID mappings
- Creates and manages symlinks
- Resolves references from either names or IDs

#### 4.2.4 KernelRegistry

Central registry of all active kernels:
- Tracks kernel connection information
- Maps kernels to their owning sessions
- Manages kernel lifecycles using MultiKernelManager

#### 4.2.5 Session

Represents a persistent computational environment:
- Contains multiple kernels
- Maintains session metadata
- Provides workspace isolation

#### 4.2.6 KernelController

Controls an individual kernel process:
- Handles direct communication with the kernel
- Processes execution results
- Manages kernel lifecycle (start, restart, stop)

## 5. Data Model and Persistence

### 5.1 Directory Structure

The Interpreter uses a filesystem-based persistence strategy with the following structure:

```
.devagent/
├── by-name/                          # Human-readable symlinks
│   ├── ProjectA/                     # Session symlink directory
│   │   ├── main -> ../../by-id/sessions/sid-123/kernels/kid-456
│   │   └── plotting -> ../../by-id/sessions/sid-123/kernels/kid-789
│   └── TaxCalculator/
│       └── main -> ../../by-id/sessions/sid-456/kernels/kid-101
├── by-id/                            # Actual storage hierarchy
│   ├── sessions/                     # Session storage by ID
│   │   ├── sid-123/                  # Session with unique ID
│   │   │   ├── metadata.json         # Session metadata
│   │   │   └── kernels/              # Kernel storage
│   │   │       ├── kid-456/          # Kernel with unique ID
│   │   │       │   ├── metadata.json # Kernel metadata
│   │   │       │   ├── connection.json # Kernel connection info
│   │   │       │   └── workspace/    # Working directory
│   │   │       └── kid-789/
│   │   │           └── ...
│   │   └── sid-456/
│   │       └── ...
│   └── kernels/                      # Global kernel information (for recovery)
│       ├── kid-456.json
│       └── ...
└── registry/                         # ID registries
    ├── sessions.json                 # Name → Session ID mapping
    └── kernels.json                  # Name → Kernel ID mapping
```

### 5.2 Key Data Structures

#### 5.2.1 Session Metadata

```json
{
  "id": "sid-123abc",
  "name": "ProjectA",
  "created_at": 1714482364.752,
  "last_activity": 1714489531.321,
  "kernels": [
    {"id": "kid-456def", "name": "main"},
    {"id": "kid-789ghi", "name": "plotting"}
  ]
}
```

#### 5.2.2 Kernel Metadata

```json
{
  "id": "kid-456def",
  "name": "main",
  "session_id": "sid-123abc",
  "kernel_type": "python3",
  "created_at": 1714482375.421,
  "last_activity": 1714489531.321
}
```

#### 5.2.3 Kernel Connection Information

```json
{
  "kernel_id": "kid-456def",
  "jupyter_kernel_id": "abc123-xyz789",
  "kernel_name": "python3",
  "connection_file": "/path/to/connection/file.json",
  "transport": "tcp",
  "started_at": 1714482380.123,
  "last_activity": 1714489531.321
}
```

#### 5.2.4 Session Registry

```json
{
  "ProjectA": "sid-123abc",
  "TaxCalculator": "sid-456def"
}
```

#### 5.2.5 Kernel Registry

```json
{
  "ProjectA/main": "kid-456def",
  "ProjectA/plotting": "kid-789ghi",
  "TaxCalculator/main": "kid-101jkl"
}
```

### 5.3 Persistence Operations

#### 5.3.1 Atomic Writes

All state changes are made atomically to ensure consistency:

```python
def atomic_write(path, data):
    """Write data to a file atomically."""
    # Write to a temporary file
    temp_path = path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Rename atomically (atomic on POSIX)
    temp_path.rename(path)
```

#### 5.3.2 Name Resolution

The system supports flexible name resolution:

```
SessionName/KernelName → lookup in registry → sid-xxx/kid-yyy
```

Or direct ID resolution:

```
sid-xxx → direct lookup in filesystem
kid-yyy → direct lookup in filesystem
```

#### 5.3.3 Recovery Process

On startup, the system scans the filesystem to rebuild its internal state:

1. Read registries to build name-to-ID mappings
2. Scan session directories to build session metadata
3. Scan kernel directories to build kernel connection info
4. Attempt to reconnect to existing kernels or start new ones as needed

## 6. Component Specifications

### 6.1 NamedResourceManager

**Responsibilities**:
- Maintain registries of human-readable names to system IDs
- Create and manage symlinks for human-readable access
- Resolve references in either direction (name→ID or ID→name)

**Key Operations**:
- `register_name(resource_type, name, system_id)`: Register a name-to-ID mapping
- `resolve_reference(reference)`: Resolve any reference form to actual path
- `create_symlink(name, target_path)`: Create a symlink for a resource
- `rename_resource(old_name, new_name)`: Rename a resource and update symlinks

**State**:
- Registry files for different resource types
- Symlink directory structure

### 6.2 SessionManager

**Responsibilities**:
- Create and manage sessions with human-readable names
- Maintain session metadata and state
- Coordinate between NamedResourceManager and Sessions

**Key Operations**:
- `create_session(name)`: Create a new session
- `get_session(reference)`: Get a session by name or ID
- `list_sessions()`: List all available sessions
- `delete_session(reference)`: Delete a session

**State**:
- Collection of active Session objects
- Reference to NamedResourceManager

### 6.3 Session

**Responsibilities**:
- Represent a persistent computational environment
- Maintain multiple kernels within the session
- Provide workspace isolation

**Key Operations**:
- `create_kernel(name, kernel_type)`: Create a new kernel in this session
- `get_kernel(reference)`: Get a kernel by name or ID
- `list_kernels()`: List all kernels in this session
- `delete_kernel(reference)`: Delete a kernel from this session

**State**:
- Session metadata (ID, name, creation time)
- References to contained kernels
- Session directory path

### 6.4 KernelRegistry

**Responsibilities**:
- Track all active kernels across all sessions
- Maintain kernel connection information
- Manage kernel lifecycles

**Key Operations**:
- `register_kernel(kernel_id, session_id, connection_info)`: Register a kernel
- `get_kernel_controller(reference)`: Get a controller for a kernel
- `list_kernels(session_id=None)`: List all kernels, optionally filtered by session
- `shutdown_kernel(kernel_id)`: Shutdown a specific kernel
- `shutdown_all()`: Shutdown all managed kernels

**State**:
- MultiKernelManager instance
- Kernel metadata and connection information

### 6.5 KernelController

**Responsibilities**:
- Control an individual kernel process
- Handle communication with the kernel
- Process execution results

**Key Operations**:
- `start_kernel()`: Start the kernel process
- `execute(code)`: Execute code in the kernel
- `interrupt()`: Interrupt the kernel's execution
- `restart()`: Restart the kernel
- `shutdown()`: Shutdown the kernel

**State**:
- Kernel metadata
- Connection information
- Reference to KernelManager

## 7. Interaction Patterns

### 7.1 Session and Kernel Creation

```
┌─────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌─────────────┐
│  Agent  │     │InterpreterAPI │     │SessionManager │     │NamedResourceMgr│     │KernelRegistry│
└────┬────┘     └───────┬───────┘     └───────┬───────┘     └───────┬───────┘     └──────┬──────┘
     │                  │                     │                     │                    │
     │ create_session("ProjectA")             │                     │                    │
     │─────────────────>│                     │                     │                    │
     │                  │ create_session("ProjectA")                │                    │
     │                  │────────────────────>│                     │                    │
     │                  │                     │ generate_session_id()                    │
     │                  │                     │────────────────────>│                    │
     │                  │                     │                     │                    │
     │                  │                     │ sid-123abc          │                    │
     │                  │                     │<────────────────────│                    │
     │                  │                     │                     │                    │
     │                  │                     │ register_name("ProjectA", sid-123abc)    │
     │                  │                     │────────────────────>│                    │
     │                  │                     │                     │                    │
     │                  │                     │ create_session_dir(sid-123abc)           │
     │                  │                     │────────────────────>│                    │
     │                  │                     │                     │                    │
     │                  │                     │ create_symlink("ProjectA", .../sid-123abc)
     │                  │                     │────────────────────>│                    │
     │                  │                     │                     │                    │
     │                  │ session             │                     │                    │
     │                  │<────────────────────│                     │                    │
     │ session          │                     │                     │                    │
     │<─────────────────│                     │                     │                    │
     │                  │                     │                     │                    │
     │ create_kernel("ProjectA/main", "python3")                    │                    │
     │─────────────────>│                     │                     │                    │
     │                  │ get_session("ProjectA")                   │                    │
     │                  │────────────────────>│                     │                    │
     │                  │                     │ resolve_reference("ProjectA")            │
     │                  │                     │────────────────────>│                    │
     │                  │                     │                     │                    │
     │                  │                     │ session_path        │                    │
     │                  │                     │<────────────────────│                    │
     │                  │                     │                     │                    │
     │                  │ session             │                     │                    │
     │                  │<────────────────────│                     │                    │
     │                  │                     │                     │                    │
     │                  │ session.create_kernel("main", "python3")  │                    │
     │                  │────────────────────────────────────────────────────────────────>
     │                  │                     │                     │                    │
     │                  │                     │                     │ start_kernel("python3")
     │                  │                     │                     │────────────────────>
     │                  │                     │                     │                    │
     │                  │                     │                     │ kernel_id          │
     │                  │                     │                     │<────────────────────
     │                  │                     │                     │                    │
     │                  │                     │                     │ register_name("ProjectA/main", kid-456def)
     │                  │                     │                     │────────────────────>
     │                  │                     │                     │                    │
     │                  │                     │                     │ create_kernel_symlink
     │                  │                     │                     │────────────────────>
     │                  │                     │                     │                    │
     │                  │ kernel              │                     │                    │
     │                  │<────────────────────────────────────────────────────────────────
     │ kernel           │                     │                     │                    │
     │<─────────────────│                     │                     │                    │
     │                  │                     │                     │                    │
```

### 7.2 Code Execution

```
┌─────────┐     ┌───────────────┐     ┌───────────────┐     ┌────────────────┐
│  Agent  │     │InterpreterAPI │     │KernelRegistry │     │KernelController│
└────┬────┘     └───────┬───────┘     └───────┬───────┘     └───────┬────────┘
     │                  │                     │                     │
     │ execute("print('hello')", "ProjectA/main")                  │
     │─────────────────>│                     │                     │
     │                  │ resolve_kernel("ProjectA/main")           │
     │                  │────────────────────>│                     │
     │                  │                     │                     │
     │                  │ kernel_controller   │                     │
     │                  │<────────────────────│                     │
     │                  │                     │                     │
     │                  │ kernel_controller.execute("print('hello')")
     │                  │─────────────────────────────────────────>│
     │                  │                     │                     │
     │                  │                     │                     │ execute code
     │                  │                     │                     │───────────┐
     │                  │                     │                     │           │
     │                  │                     │                     │<──────────┘
     │                  │                     │                     │
     │                  │                     │                     │ collect results
     │                  │                     │                     │───────────┐
     │                  │                     │                     │           │
     │                  │                     │                     │<──────────┘
     │                  │                     │                     │
     │                  │ execution_result    │                     │
     │                  │<─────────────────────────────────────────│
     │                  │                     │                     │
     │ execution_result │                     │                     │
     │<─────────────────│                     │                     │
     │                  │                     │                     │
```

### 7.3 Session Recovery

```
┌─────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Agent  │     │InterpreterAPI │     │SessionManager │     │KernelRegistry │
└────┬────┘     └───────┬───────┘     └───────┬───────┘     └───────┬───────┘
     │                  │                     │                     │
     │ initialize()     │                     │                     │
     │─────────────────>│                     │                     │
     │                  │ recover_state()     │                     │
     │                  │────────────────────>│                     │
     │                  │                     │                     │
     │                  │                     │ scan_session_directories()
     │                  │                     │─────────────────────┐
     │                  │                     │                     │
     │                  │                     │<────────────────────┘
     │                  │                     │                     │
     │                  │                     │ restore_kernels()   │
     │                  │                     │────────────────────>│
     │                  │                     │                     │
     │                  │                     │                     │ scan_kernel_connection_files()
     │                  │                     │                     │─────────────────────┐
     │                  │                     │                     │                     │
     │                  │                     │                     │<────────────────────┘
     │                  │                     │                     │
     │                  │                     │                     │ try_reconnect_kernels()
     │                  │                     │                     │─────────────────────┐
     │                  │                     │                     │                     │
     │                  │                     │                     │<────────────────────┘
     │                  │                     │                     │
     │                  │                     │ kernels_restored    │
     │                  │                     │<────────────────────│
     │                  │                     │                     │
     │                  │ state_recovered     │                     │
     │                  │<────────────────────│                     │
     │                  │                     │                     │
     │ ready            │                     │                     │
     │<─────────────────│                     │                     │
     │                  │                     │                     │
```

## 8. Implementation Considerations

### 8.1 Atomic Operations

All file operations should be atomic to prevent data corruption:

- Use temporary files and atomic renames for writing metadata
- Use file locks for operations that span multiple files
- Implement transaction-like patterns for multi-step operations

### 8.2 Race Condition Prevention

When multiple processes might access the same resources:

- Use file-based locking for critical sections
- Implement optimistic concurrency control with version checking
- Handle "lost update" scenarios gracefully

### 8.3 Error Recovery

The system should be resilient to interruptions:

- Detect and repair inconsistent state during startup
- Implement cleanup routines for incomplete operations
- Log operations with enough detail to reconstruct state

### 8.4 Platform Compatibility

Consider compatibility across different operating systems:

- Abstract filesystem operations that might differ (e.g., symlinks on Windows)
- Use relative paths where possible for relocatability
- Handle path length limitations and special characters

### 8.5 Performance Optimization

For efficiency with many sessions/kernels:

- Implement lazy loading of session/kernel data
- Cache resolved paths and metadata
- Use bulk operations where possible

## 9. Security Considerations

### 9.1 Filesystem Permissions

- Set appropriate permissions on all created files and directories
- Restrict access to connection files containing authentication tokens
- Validate all paths to prevent directory traversal attacks

### 9.2 Kernel Isolation

- Apply resource limits to kernel processes
- Run kernels in isolated environments when possible
- Implement timeouts for long-running operations

### 9.3 Input Validation

- Validate all user-provided names and references
- Sanitize code before execution
- Handle error conditions gracefully

## 10. Appendix

### 10.1 Glossary

- **Session**: A persistent computational environment with multiple kernels
- **Kernel**: A computational process that executes code
- **Symlink**: A filesystem link that points to another location
- **Registry**: A mapping between human-readable names and system identifiers
- **Resource Manager**: A component that handles name-to-ID resolution and symlinks

### 10.2 References

- Jupyter Client API: [Documentation](https://jupyter-client.readthedocs.io/)
- ZeroMQ Messaging: [Documentation](https://zeromq.org/socket-api/)
- POSIX File Operations: [Standard](https://pubs.opengroup.org/onlinepubs/9699919799/functions/contents.html)
- Hierarchical Domain Design: Reference document