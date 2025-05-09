"""
The Package Entrypoint
"""

from __future__ import annotations
import argparse
import logging
import os
import sys
import pathlib
import json
import contextlib
from typing import Union, Any, TextIO, Optional
from collections import deque

from DevAgent.api import InterpreterAPI, OntologyAPI
from DevAgent.interpreter.compat import DualModeInterpreter

SCRIPT = pathlib.Path(__file__)
CONTEXT = SCRIPT.parent  # The context of Script
logger = logging.getLogger(__package__ if __name__ == "__main__" else __name__)


def handle_ontology_init(args: argparse.Namespace) -> bool:
    """Initialize a new ontology graph."""
    graph = OntologyAPI.init()
    
    # Output graph to stdout or file
    if args.output == "-":
        json.dump(OntologyAPI.dump(graph), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        with open(args.output, "w") as f:
            json.dump(OntologyAPI.dump(graph), f, indent=2)
    
    return True


def handle_ontology_info(args: argparse.Namespace) -> bool:
    """Display information about an ontology graph."""
    # Load graph from stdin or file
    if args.input == "-":
        graph = OntologyAPI.load(json.load(sys.stdin))
    else:
        with open(args.input) as f:
            graph = OntologyAPI.load(json.load(f))
    
    # Display graph info
    nodes, edges = OntologyAPI.info(graph)
    sys.stdout.write(f"nodes={nodes} edges={edges}\n")
    
    return True


def handle_ontology_dump(args: argparse.Namespace) -> bool:
    """Dump ontology graph to stdout or file."""
    # Load graph from stdin or file
    if args.input == "-":
        graph = OntologyAPI.load(json.load(sys.stdin))
    else:
        with open(args.input) as f:
            graph = OntologyAPI.load(json.load(f))
    
    # Output graph to stdout or file
    if args.output == "-":
        json.dump(OntologyAPI.dump(graph), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        with open(args.output, "w") as f:
            json.dump(OntologyAPI.dump(graph), f, indent=2)
    
    return True


def handle_ontology_add_node(args: argparse.Namespace) -> bool:
    """Add a node to the ontology graph."""
    # Load graph from stdin or file
    if args.input == "-":
        graph = OntologyAPI.load(json.load(sys.stdin))
    else:
        with open(args.input) as f:
            graph = OntologyAPI.load(json.load(f))
    
    # Parse metadata
    try:
        meta = json.loads(args.meta)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON metadata: {args.meta}")
        return False
    
    # Add node
    OntologyAPI.add_node(graph, args.id, args.label, args.kind, meta)
    
    # Output updated graph
    if args.output == "-":
        json.dump(OntologyAPI.dump(graph), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        with open(args.output, "w") as f:
            json.dump(OntologyAPI.dump(graph), f, indent=2)
    
    return True


def handle_ontology_add_edge(args: argparse.Namespace) -> bool:
    """Add an edge to the ontology graph."""
    # Load graph from stdin or file
    if args.input == "-":
        graph = OntologyAPI.load(json.load(sys.stdin))
    else:
        with open(args.input) as f:
            graph = OntologyAPI.load(json.load(f))
    
    # Add edge
    OntologyAPI.add_edge(graph, args.src, args.rel, args.dst)
    
    # Output updated graph
    if args.output == "-":
        json.dump(OntologyAPI.dump(graph), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        with open(args.output, "w") as f:
            json.dump(OntologyAPI.dump(graph), f, indent=2)
    
    return True


def handle_interpreter_session_create(args: argparse.Namespace) -> bool:
    """Create a new interpreter session."""
    # Create API instance
    base_dir_path = pathlib.Path(args.dir)
    
    # Use DualModeInterpreter for the new DDD architecture by default
    interpreter = DualModeInterpreter(base_dir_path, use_ddd=not args.legacy)
    
    try:
        # Create session
        result = interpreter.create_session(args.name)
        if result["success"]:
            sys.stdout.write(f"Session created: {args.name}\n")
            sys.stdout.write(f"Session ID: {result['session_id']}\n")
            return True
        else:
            logger.error(f"Failed to create session: {result['error']}")
            return False
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        return False


def handle_interpreter_session_list(args: argparse.Namespace) -> bool:
    """List all interpreter sessions."""
    # Create API instance
    base_dir_path = pathlib.Path(args.dir)
    
    # Use DualModeInterpreter for the new DDD architecture by default
    interpreter = DualModeInterpreter(base_dir_path, use_ddd=not args.legacy)
    
    try:
        # List sessions
        result = interpreter.list_sessions()
        if result["success"]:
            sessions = result["sessions"]
            if sessions:
                sys.stdout.write("Active sessions:\n")
                for session in sessions:
                    sys.stdout.write(f"  ID: {session['id']}, Name: {session['name']}\n")
                    if 'kernel_count' in session:
                        sys.stdout.write(f"    Kernels: {session['kernel_count']}\n")
                    if 'path' in session:
                        sys.stdout.write(f"    Path: {session['path']}\n")
            else:
                sys.stdout.write("No active sessions\n")
            return True
        else:
            logger.error(f"Failed to list sessions: {result['error']}")
            return False
    except Exception as e:
        logger.error(f"Failed to list sessions: {str(e)}")
        return False


def handle_interpreter_session_delete(args: argparse.Namespace) -> bool:
    """Delete an interpreter session."""
    # Create API instance
    base_dir_path = pathlib.Path(args.dir)
    
    # Use DualModeInterpreter for the new DDD architecture by default
    interpreter = DualModeInterpreter(base_dir_path, use_ddd=not args.legacy)
    
    try:
        # Delete session
        result = interpreter.delete_session(args.session)
        if result["success"]:
            sys.stdout.write(f"Session '{args.session}' deleted successfully\n")
            return True
        else:
            logger.error(f"Failed to delete session: {result['error']}")
            return False
    except Exception as e:
        logger.error(f"Failed to delete session: {str(e)}")
        return False


def handle_interpreter_session_execute(args: argparse.Namespace) -> bool:
    """Execute code in a session."""
    # Create API instance
    base_dir_path = pathlib.Path(args.dir)
    
    # Construct kernel reference
    kernel_ref = f"{args.session}/{args.kernel}"
    
    # Use DualModeInterpreter for the new DDD architecture by default
    interpreter = DualModeInterpreter(base_dir_path, use_ddd=not args.legacy)
    
    try:
        # Execute code
        result = interpreter.execute_code(kernel_ref, args.code)
        
        # Display output
        if result["stdout"]:
            sys.stdout.write(result["stdout"])
            # Add newline if not already present
            if not result["stdout"].endswith("\n"):
                sys.stdout.write("\n")
        
        # Display error if any
        if result["error"]:
            sys.stdout.write("ERROR:\n")
            sys.stdout.write(result["error"])
            sys.stdout.write("\n")
        
        return result["success"]
    except Exception as e:
        logger.error(f"Failed to execute code: {str(e)}")
        return False


def handle_interpreter_kernel_create(args: argparse.Namespace) -> bool:
    """Create a new kernel in a session."""
    # Create API instance
    base_dir_path = pathlib.Path(args.dir)
    
    # Use DualModeInterpreter for the new DDD architecture by default
    interpreter = DualModeInterpreter(base_dir_path, use_ddd=not args.legacy)
    
    try:
        # Create kernel
        result = interpreter.create_kernel(args.session, args.name, args.type)
        if result["success"]:
            sys.stdout.write(f"Kernel created: {args.name}\n")
            sys.stdout.write(f"Kernel ID: {result['kernel_id']}\n")
            sys.stdout.write(f"Kernel Type: {args.type}\n")
            sys.stdout.write(f"In Session: {args.session}\n")
            return True
        else:
            logger.error(f"Failed to create kernel: {result['error']}")
            return False
    except Exception as e:
        logger.error(f"Failed to create kernel: {str(e)}")
        return False


def handle_interpreter_kernel_list(args: argparse.Namespace) -> bool:
    """List kernels in a session."""
    # Create API instance
    base_dir_path = pathlib.Path(args.dir)
    
    # Use legacy API directly for now as list_kernels isn't fully implemented in DualModeInterpreter
    api = InterpreterAPI(base_dir_path)
    
    try:
        # Get session
        session = api.get_session(args.session)
        if not session:
            logger.error(f"Session '{args.session}' not found")
            return False
        
        # List kernels
        kernels = session.list_kernels()
        if kernels:
            sys.stdout.write(f"Kernels in session '{args.session}':\n")
            for kernel in kernels:
                status = "alive" if kernel.get("alive", False) else "dead"
                sys.stdout.write(f"  {kernel['name']} (ID: {kernel['id']}, Type: {kernel.get('kernel_type', 'unknown')}, Status: {status})\n")
        else:
            sys.stdout.write(f"No kernels in session '{args.session}'\n")
        return True
    except Exception as e:
        logger.error(f"Failed to list kernels: {str(e)}")
        return False


def handle_interpreter_kernel_execute(args: argparse.Namespace) -> bool:
    """Execute code in a kernel."""
    # Create API instance
    base_dir_path = pathlib.Path(args.dir)
    
    # Use DualModeInterpreter for the new DDD architecture by default
    interpreter = DualModeInterpreter(base_dir_path, use_ddd=not args.legacy)
    
    try:
        # Execute code
        if args.file:
            # Read code from file
            with open(args.file, 'r') as f:
                code = f.read()
        else:
            code = args.code
        
        # Execute code
        result = interpreter.execute_code(args.ref, code)
        
        # Display output
        if result["stdout"]:
            sys.stdout.write(result["stdout"])
            # Add newline if not already present
            if not result["stdout"].endswith("\n"):
                sys.stdout.write("\n")
        
        # Display error if any
        if result["error"]:
            sys.stdout.write("ERROR:\n")
            sys.stdout.write(result["error"])
            sys.stdout.write("\n")
        
        return result["success"]
    except Exception as e:
        logger.error(f"Failed to execute code: {str(e)}")
        return False


def handle_interpreter_kernel_restart(args: argparse.Namespace) -> bool:
    """Restart a kernel."""
    # Create API instance
    base_dir_path = pathlib.Path(args.dir)
    
    # Use DualModeInterpreter for the new DDD architecture by default
    interpreter = DualModeInterpreter(base_dir_path, use_ddd=not args.legacy)
    
    try:
        # Restart kernel
        result = interpreter.restart_kernel(args.ref)
        if result["success"]:
            sys.stdout.write(f"Kernel '{args.ref}' restarted successfully\n")
            return True
        else:
            logger.error(f"Failed to restart kernel: {result['error']}")
            return False
    except Exception as e:
        logger.error(f"Failed to restart kernel: {str(e)}")
        return False


def handle_interpreter_kernel_interrupt(args: argparse.Namespace) -> bool:
    """Interrupt a kernel."""
    # Create API instance
    base_dir_path = pathlib.Path(args.dir)
    
    # Use DualModeInterpreter for the new DDD architecture by default
    interpreter = DualModeInterpreter(base_dir_path, use_ddd=not args.legacy)
    
    try:
        # Interrupt kernel
        result = interpreter.interrupt_kernel(args.ref)
        if result["success"]:
            sys.stdout.write(f"Kernel '{args.ref}' interrupted successfully\n")
            return True
        else:
            logger.error(f"Failed to interrupt kernel: {result['error']}")
            return False
    except Exception as e:
        logger.error(f"Failed to interrupt kernel: {str(e)}")
        return False


def handle_interpreter_kernel_delete(args: argparse.Namespace) -> bool:
    """Delete a kernel."""
    # Create API instance
    base_dir_path = pathlib.Path(args.dir)
    
    # Use DualModeInterpreter for the new DDD architecture by default
    interpreter = DualModeInterpreter(base_dir_path, use_ddd=not args.legacy)
    
    try:
        # Delete kernel
        result = interpreter.delete_kernel(args.ref)
        if result["success"]:
            sys.stdout.write(f"Kernel '{args.ref}' deleted successfully\n")
            return True
        else:
            logger.error(f"Failed to delete kernel: {result['error']}")
            return False
    except Exception as e:
        logger.error(f"Failed to delete kernel: {str(e)}")
        return False


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="DevAgent: Agentic Development Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Common arguments for all commands
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # === Ontology commands ===
    ontology_parser = subparsers.add_parser("ontology", help="Ontology graph operations")
    ontology_subparsers = ontology_parser.add_subparsers(dest="subcommand", help="Ontology operation")
    
    # Ontology init
    init_parser = ontology_subparsers.add_parser("init", help="Initialize a new ontology graph")
    init_parser.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
    init_parser.set_defaults(func=handle_ontology_init)
    
    # Ontology info
    info_parser = ontology_subparsers.add_parser("info", help="Display ontology graph information")
    info_parser.add_argument("-f", "--input", default="-", help="Input file (default: stdin)")
    info_parser.set_defaults(func=handle_ontology_info)
    
    # Ontology dump
    dump_parser = ontology_subparsers.add_parser("dump", help="Dump ontology graph")
    dump_parser.add_argument("-f", "--input", default="-", help="Input file (default: stdin)")
    dump_parser.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
    dump_parser.set_defaults(func=handle_ontology_dump)
    
    # Ontology add-node
    add_node_parser = ontology_subparsers.add_parser("add-node", help="Add a node to the ontology graph")
    add_node_parser.add_argument("-f", "--input", default="-", help="Input file (default: stdin)")
    add_node_parser.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
    add_node_parser.add_argument("id", help="Node ID")
    add_node_parser.add_argument("label", help="Node label")
    add_node_parser.add_argument("--kind", default="concept", help="Node kind (default: concept)")
    add_node_parser.add_argument("--meta", default="{}", help="Node metadata as JSON string")
    add_node_parser.set_defaults(func=handle_ontology_add_node)
    
    # Ontology add-edge
    add_edge_parser = ontology_subparsers.add_parser("add-edge", help="Add an edge to the ontology graph")
    add_edge_parser.add_argument("-f", "--input", default="-", help="Input file (default: stdin)")
    add_edge_parser.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
    add_edge_parser.add_argument("src", help="Source node ID")
    add_edge_parser.add_argument("rel", help="Relationship type")
    add_edge_parser.add_argument("dst", help="Destination node ID")
    add_edge_parser.set_defaults(func=handle_ontology_add_edge)
    
    # === Interpreter commands ===
    interpreter_parser = subparsers.add_parser("interpreter", help="Interpreter operations")
    interpreter_parser.add_argument(
        "--dir",
        default=str(pathlib.Path.cwd() / '.devagent'),
        help="Base directory for interpreter files"
    )
    interpreter_parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy interpreter implementation instead of the new DDD architecture"
    )
    
    interpreter_subparsers = interpreter_parser.add_subparsers(dest="subcommand", help="Interpreter operation")
    
    # Session commands
    session_parser = interpreter_subparsers.add_parser("session", help="Session management operations")
    session_subparsers = session_parser.add_subparsers(dest="session_command", help="Session operation")
    
    # Session create
    session_create_parser = session_subparsers.add_parser("create", help="Create a new session")
    session_create_parser.add_argument("--name", default="main", help="Session name (default: main)")
    session_create_parser.set_defaults(func=handle_interpreter_session_create)
    
    # Session list
    session_list_parser = session_subparsers.add_parser("list", help="List all sessions")
    session_list_parser.set_defaults(func=handle_interpreter_session_list)
    
    # Session delete
    session_delete_parser = session_subparsers.add_parser("delete", help="Delete a session")
    session_delete_parser.add_argument("session", help="Session reference (name or ID)")
    session_delete_parser.set_defaults(func=handle_interpreter_session_delete)
    
    # Session execute
    session_execute_parser = session_subparsers.add_parser("execute", help="Execute code in a session")
    session_execute_parser.add_argument("--session", default="main", help="Session reference (default: main)")
    session_execute_parser.add_argument("--kernel", default="main", help="Kernel name (default: main)")
    session_execute_parser.add_argument("--code", required=True, help="Code to execute")
    session_execute_parser.set_defaults(func=handle_interpreter_session_execute)
    
    # Kernel commands
    kernel_parser = interpreter_subparsers.add_parser("kernel", help="Kernel management operations")
    kernel_subparsers = kernel_parser.add_subparsers(dest="kernel_command", help="Kernel operation")
    
    # Kernel create
    kernel_create_parser = kernel_subparsers.add_parser("create", help="Create a new kernel")
    kernel_create_parser.add_argument("--session", required=True, help="Session reference")
    kernel_create_parser.add_argument("--name", default="main", help="Kernel name (default: main)")
    kernel_create_parser.add_argument("--type", default="python3", help="Kernel type (default: python3)")
    kernel_create_parser.set_defaults(func=handle_interpreter_kernel_create)
    
    # Kernel list
    kernel_list_parser = kernel_subparsers.add_parser("list", help="List kernels in a session")
    kernel_list_parser.add_argument("--session", required=True, help="Session reference")
    kernel_list_parser.set_defaults(func=handle_interpreter_kernel_list)
    
    # Kernel execute
    kernel_execute_parser = kernel_subparsers.add_parser("execute", help="Execute code in a kernel")
    kernel_execute_parser.add_argument("--ref", required=True, help="Kernel reference (session/kernel or kernel ID)")
    code_group = kernel_execute_parser.add_mutually_exclusive_group(required=True)
    code_group.add_argument("--code", help="Code to execute")
    code_group.add_argument("--file", help="File containing code to execute")
    kernel_execute_parser.set_defaults(func=handle_interpreter_kernel_execute)
    
    # Kernel restart
    kernel_restart_parser = kernel_subparsers.add_parser("restart", help="Restart a kernel")
    kernel_restart_parser.add_argument("--ref", required=True, help="Kernel reference")
    kernel_restart_parser.set_defaults(func=handle_interpreter_kernel_restart)
    
    # Kernel interrupt
    kernel_interrupt_parser = kernel_subparsers.add_parser("interrupt", help="Interrupt a kernel")
    kernel_interrupt_parser.add_argument("--ref", required=True, help="Kernel reference")
    kernel_interrupt_parser.set_defaults(func=handle_interpreter_kernel_interrupt)
    
    # Kernel delete
    kernel_delete_parser = kernel_subparsers.add_parser("delete", help="Delete a kernel")
    kernel_delete_parser.add_argument("--ref", required=True, help="Kernel reference")
    kernel_delete_parser.set_defaults(func=handle_interpreter_kernel_delete)
    
    return parser


class CLI:
    @classmethod
    @contextlib.contextmanager
    def session(cls):
        try:
            try:
                logging.basicConfig(stream=sys.stderr, level=os.environ.get("LOG_LEVEL", "INFO"))
            except Exception as e:
                logging.basicConfig(stream=sys.stderr, level="INFO")
                logger.critical(f"Bad Log Configuration: {e}")
                yield False
            else:
                logger.debug("inizio")
                yield True  # Any CLI Exceptions will be raised here
        except (SystemExit,): ...
        except: logger.critical("Unhandled Exception", exc_info=True)
        finally:
            logger.debug("fin")
            logging.shutdown()
            sys.stdout.flush()
            sys.stderr.flush()


def main() -> int:
    """Main entry point for the program."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # If no command is specified, show help
    if not hasattr(args, "func"):
        if hasattr(args, "subcommand") and args.subcommand is None:
            # Show help for the specific command
            if args.command == "ontology":
                parser._actions[1].choices["ontology"].print_help()
            elif args.command == "interpreter":
                parser._actions[1].choices["interpreter"].print_help()
            else:
                parser.print_help()
        elif args.command is None:
            parser.print_help()
        return 1
    
    # Execute the appropriate handler
    success = args.func(args)
    return 0 if success else 1


if __name__ == "__main__":
    with CLI.session() as ok:
        if ok:
            exit_code = main()
            sys.exit(exit_code)
        else:
            sys.exit(2)