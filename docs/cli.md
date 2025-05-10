# DevAgent CLI

The DevAgent CLI provides a command-line interface for interacting with the DevAgent tools, including the Interpreter and Ontology components.

## Architecture

The CLI has been refactored to use:

1. Modern Python `argparse` for robust command-line argument handling
2. Domain-Driven Design (DDD) architecture for the Interpreter component
3. Event-driven architecture with persistent kernel processes
4. Comprehensive test coverage with unit and integration tests

The new event-driven DDD architecture provides:
- Cleaner separation of concerns
- Better testability
- More maintainable code
- Persistent kernel processes that continue running after CLI commands complete
- Automatic reconciliation between desired and actual state

## Commands

### Ontology Commands

The DevAgent CLI provides commands for working with ontology graphs.

```bash
# Initialize a new ontology graph
python -m DevAgent ontology init -o graph.json

# Display information about an ontology graph
python -m DevAgent ontology info -f graph.json

# Dump an ontology graph
python -m DevAgent ontology dump -f graph.json -o output.json

# Add a node to an ontology graph
python -m DevAgent ontology add-node -f graph.json -o graph.json node1 "Node 1" --kind=concept --meta='{"foo": "bar"}'

# Add an edge to an ontology graph
python -m DevAgent ontology add-edge -f graph.json -o graph.json node1 RELATED_TO node2
```

### Interpreter Commands

The Interpreter component allows you to create and manage computational sessions and kernels.

#### Session Commands

```bash
# Create a new session
python -m DevAgent interpreter session create --name=my_session

# List all sessions
python -m DevAgent interpreter session list

# Execute code in a session
python -m DevAgent interpreter session execute --session=my_session --kernel=main --code="print('hello world')"

# Delete a session
python -m DevAgent interpreter session delete my_session
```

#### Kernel Commands

```bash
# Create a new kernel in a session (will start in the background)
python -m DevAgent interpreter kernel create --session=my_session --name=my_kernel --type=python3

# List kernels in a session
python -m DevAgent interpreter kernel list --session=my_session

# Execute code in a kernel
python -m DevAgent interpreter kernel execute --ref=my_session/my_kernel --code="print('hello world')"
# OR execute code from a file
python -m DevAgent interpreter kernel execute --ref=my_session/my_kernel --file=script.py

# Restart a kernel
python -m DevAgent interpreter kernel restart --ref=my_session/my_kernel

# Interrupt a kernel
python -m DevAgent interpreter kernel interrupt --ref=my_session/my_kernel

# Delete a kernel
python -m DevAgent interpreter kernel delete --ref=my_session/my_kernel

# Get the status of a kernel
python -m DevAgent interpreter kernel status --ref=my_session/my_kernel

# Start a kernel (if not already running)
python -m DevAgent interpreter kernel start --ref=my_session/my_kernel

# Stop a kernel
python -m DevAgent interpreter kernel stop --ref=my_session/my_kernel
```

## Persistent Kernel Architecture

DevAgent now supports persistent kernel processes that continue running even after CLI commands exit. This enables more efficient workflows:

1. **Create a kernel once, use it repeatedly**: Kernel processes stay alive across CLI invocations
2. **View kernel status**: Use the `status` command to check if kernels are running
3. **Explicit process control**: Use `start` and `stop` commands to manually control kernels
4. **Process reconciliation**: DevAgent continuously monitors and reconciles kernel processes to ensure desired state matches actual state

### Example Workflow

```bash
# Create a session
python -m DevAgent interpreter session create --name data_analysis

# Create a Python kernel (this starts the kernel in the background)
python -m DevAgent interpreter kernel create --session data_analysis --name python3 --type python3

# Check kernel status (will show RUNNING if started successfully)
python -m DevAgent interpreter kernel status --ref data_analysis/python3

# Execute code in the kernel (quickly - no kernel startup delay)
python -m DevAgent interpreter kernel execute --ref data_analysis/python3 --code "import numpy as np; np.random.rand(3,3)"

# Execute another command (kernel is still running)
python -m DevAgent interpreter kernel execute --ref data_analysis/python3 --code "import pandas as pd; pd.DataFrame({'a': [1,2,3]})"

# Stop the kernel when done
python -m DevAgent interpreter kernel stop --ref data_analysis/python3
```

### How It Works

The persistent kernel architecture works using:

1. **Event-driven communication**: Commands publish events to a filesystem-based event bus
2. **Dual-state model**: System tracks both desired and actual state of kernels
3. **Kernel operator**: Continuously reconciles actual state with desired state
4. **State persistence**: Runtime state is persisted to the filesystem
5. **Cooperative processing**: Multiple CLI processes cooperate via the event system

This allows kernels to remain running even when no DevAgent CLI processes are active.

## Testing

The CLI comes with comprehensive tests, including unit tests and integration tests.

### Running Tests

```bash
# Run all tests
python -m tests.run_cli_tests

# Run only unit tests
python -m tests.run_cli_tests --unit-only

# Run only integration tests
python -m tests.run_cli_tests --integration-only

# Run tests with verbose output
python -m tests.run_cli_tests -v
```

### Test Structure

- `tests/test_cli.py`: Unit tests for the CLI
- `tests/test_cli_integration.py`: Integration tests for the CLI
- `tests/run_cli_tests.py`: Test runner script

## Contributing

When making changes to the CLI, please ensure:

1. All tests pass
2. The architecture remains clean and maintainable
3. New features follow the existing command structure
4. Documentation is updated