"""
DevAgent Interpreter Architecture

This module defines the architecture for DevAgent's interpreter system, which provides
computational environments for agents through a managed Jupyter infrastructure.

# Usage

An Execution Environment is the single point of integration into the Development
Environment for both human developers, development agents & standard automations.
The Execution Environment provides a realtime, programmatic way to interact with
a project such as for:

- Query & Search
- File Manipulation
- Git & Source Control
- Tests & Debugging
- Documentation

The Exeuction Environment does not allow for arbitrary code execution; every connecting
entity must first authenticate themselves to gain access to a session of certain
permissions. Permissions may never be elevated during the lifetime of a session.

# Architecture Overview

The interpreter system is designed with clean separation of concerns, dividing
responsibilities into four main components:

1. ServerController: Manages the lifecycle of the Jupyter Server process
2. KernelController: Manages kernels running within a Jupyter Server
3. StateManager: Handles persistence of interpreter and kernel state
4. InterpreterManager: Provides a unified interface for interpreter sessions

# Component Relationships

- InterpreterManager uses ServerController to manage server processes
- InterpreterManager uses StateManager to persist interpreter state
- InterpreterManager uses KernelController to manage kernels
- KernelController uses the Jupyter Server API to interact with kernels
- KernelController uses StateManager to persist kernel state
- ServerController is independent and manages only the server process

# Data Flow

1. InterpreterManager is the primary point of entry
2. For server operations, it delegates to ServerController
3. For kernel operations, it obtains a KernelController and delegates operations
4. KernelController performs operations via Jupyter Server API
5. Both controllers use StateManager to persist and retrieve state

This architecture ensures:
- Clear separation of responsibilities
- Explicit dependencies
- Centralized state management
- Clean interfaces between components
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path

from .server import ServerController
from .session import StateManager, KernelController, SessionManager

__all__ = ['ServerController', 'StateManager', 'KernelController', 'SessionManager']
