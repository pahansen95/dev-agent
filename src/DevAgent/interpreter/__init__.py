"""
DevAgent Interpreter - The computational bridge for development agents.

This package provides a filesystem-based persistent environment for executing code
and managing computational sessions. It directly integrates with Jupyter kernels
without the need for a Jupyter Server, enabling robust code execution capabilities
within the DevAgent ecosystem.

Key features:
- Session-based computation environments with multiple kernels
- Direct Jupyter kernel integration without Jupyter Server dependencies
- Persistent filesystem storage for sessions and kernels
- Flexible naming and reference resolution system
- Thread-safe operations with atomic file operations

The primary entry point is the InterpreterAPI class, which provides methods for
creating and managing sessions and kernels.

Example usage:
    ```python
    from DevAgent.interpreter import InterpreterAPI
    
    # Create API instance
    api = InterpreterAPI()
    
    # Create a session
    session = api.create_session("my-project")
    
    # Create a kernel in the session
    api.create_kernel("my-project", "main")
    
    # Execute code
    result = api.execute_code("my-project/main", "print('Hello, world!')")
    print(result.stdout)  # "Hello, world!"
    ```
"""

from .api import InterpreterAPI
from .session import Session, SessionManager
from .kernel import KernelController, ExecutionResult
from .registry import Registry

__all__ = ['InterpreterAPI', 'Session', 'SessionManager', 'KernelController', 'ExecutionResult', 'Registry']

# Version information
__version__ = '2.0.0'
