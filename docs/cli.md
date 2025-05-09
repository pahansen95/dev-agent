# DevAgent CLI

The DevAgent CLI provides a command-line interface for interacting with the DevAgent tools, including the Interpreter and Ontology components.

## Architecture

The CLI has been refactored to use:

1. Modern Python `argparse` for robust command-line argument handling
2. Domain-Driven Design (DDD) architecture for the Interpreter component
3. Comprehensive test coverage with unit and integration tests

The new DDD architecture provides a cleaner separation of concerns, better testability, and more maintainable code. The CLI integrates with this architecture through the `DualModeInterpreter` compatibility layer, which allows for a smooth transition from the legacy architecture to the new DDD-based implementation.

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
# Create a new kernel in a session
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
```

## Legacy Mode

The CLI can operate in both the new DDD-based architecture (default) and the legacy architecture. To use the legacy architecture, add the `--legacy` flag to any interpreter command:

```bash
python -m DevAgent interpreter --legacy session create --name=my_session
```

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