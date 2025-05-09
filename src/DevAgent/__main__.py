"""
The Package Entrypoint

"""

from __future__ import annotations
from typing import *
from collections.abc import *
from types import *
from typing import Callable, Union, Any

import logging, os, sys, contextlib, pathlib, json, time
from collections import deque
from DevAgent.api import *

SCRIPT = pathlib.Path(__file__)
CONTEXT = SCRIPT.parent # The context of Script
logger = logging.getLogger(__package__ if __name__ == "__main__" else __name__)

def handle_ontology(
  pop_arg: Callable[[str], str],
  get_kwarg: Callable[[str, Union[str, bool, Any]], str],
  env: dict[str, str],
  stdin: TextIO,
  stdout: TextIO,
  kwargs: dict[str, str],
  remainder: deque[str],
  E: type[Exception],
):
  op = pop_arg("operation") # e.g. "init", "info", "dump", "add-node", "add-edge"
  # support both "init" and "create" as synonyms if you like
  in_f = get_kwarg("f", "-") # input JSON file (or '-' for stdin)
  out_f = get_kwarg("o", "-") # output file

  graph = (None if op in ("init", "create") else OntologyAPI.load(json.load(open(in_f) if in_f != "-" else stdin)))

  match op:
    case "init" | "create":
      graph = OntologyAPI.init()
    case "info":
      n, e = OntologyAPI.info(graph)
      stdout.write(f"nodes={n} edges={e}\n")
      return
    case "dump":
      json.dump(
        OntologyAPI.dump(graph),
        open(out_f, "w") if out_f != "-" else stdout,
        indent=2,
      )
      return
    case "add-node":
      id_, lbl = pop_arg("ID"), pop_arg("LABEL")
      kind = kwargs.get("kind", "concept")
      meta = json.loads(kwargs.get("meta", "{}"))
      OntologyAPI.add_node(graph, id_, lbl, kind, meta)
    case "add-edge":
      src, rel, dst = (pop_arg(k) for k in ("SRC", "REL", "DST"))
      OntologyAPI.add_edge(graph, src, rel, dst)
    case _:
      raise E(f"Unknown ontology operation: {op}")

  # for mutating ops we write back the updated graph
  json.dump(OntologyAPI.dump(graph), open(out_f, "w") if out_f != "-" else stdout, indent=2)
  stdout.write("\n")

def handle_interpreter_session(
  pop_arg: Callable[[str], str],
  get_kwarg: Callable[[str, Union[str, bool, Any]], str],
  env: dict[str, str],
  stdin: TextIO,
  stdout: TextIO,
  kwargs: dict[str, str],
  remainder: Deque[str],
  E: type[Exception],
):
  """
  Handle the 'interpreter session' subcommand.
  
  Supports the following actions:
  - create: Create a new session
  - list: List all active sessions
  - execute: Execute code in a session
  - delete: Delete a session
  
  Examples:
    python -m DevAgent interpreter session create
    python -m DevAgent interpreter session create --name=dev_session
    python -m DevAgent interpreter session list
    python -m DevAgent interpreter session execute --code="print('hello')" --session=dev_session
  """
  # Get the session action
  try:
    action = pop_arg("action")
  except Exception:
    # Show usage if no action provided
    stdout.write("Usage: python -m DevAgent interpreter session <action> [options]\n")
    stdout.write("Actions: create, list, execute, delete\n")
    return

  # Get base directory from kwargs or use current directory
  try:
    base_dir = get_kwarg("dir")
    base_dir_path = pathlib.Path(base_dir)
  except:
    base_dir_path = pathlib.Path(os.getcwd()) / '.devagent'

  # Create the API instance
  api = InterpreterAPI(base_dir_path)

  # Handle different session actions
  if action == "create":
    # Get optional session name
    try:
      session_name = get_kwarg("name", "main")
    except:
      session_name = "main"

    try:
      # Create a session
      session = api.create_session(session_name)
      stdout.write(f"Session created: {session_name}\n")
      stdout.write(f"Session ID: {session.id}\n")
      stdout.write(f"Session directory: {session.path}\n")
    except Exception as e:
      raise E(f"Failed to create session: {str(e)}")

  elif action == "list":
    try:
      # List active sessions
      sessions = api.list_sessions()
      if sessions:
        stdout.write("Active sessions:\n")
        for session_info in sessions:
          stdout.write(f"  ID: {session_info['id']}, Name: {session_info['name']}\n")
          if 'kernels' in session_info and session_info['kernels']:
            stdout.write(f"    Kernels: {len(session_info['kernels'])}\n")
          stdout.write(f"    Path: {session_info.get('path', 'unknown')}\n")
      else:
        stdout.write("No active sessions\n")
    except Exception as e:
      raise E(f"Failed to list sessions: {str(e)}")

  elif action == "execute":
    # Get required code and session/kernel reference
    code = get_kwarg("code")

    try:
      session_ref = get_kwarg("session", "main")
    except:
      session_ref = "main"

    try:
      kernel_name = get_kwarg("kernel", "main")
    except:
      kernel_name = "main"

    try:
      # Execute the code
      kernel_ref = f"{session_ref}/{kernel_name}"
      result = api.execute_code(kernel_ref, code)

      # Display output
      if result.stdout:
        stdout.write(result.stdout)
        # Add newline if not already present
        if not result.stdout.endswith("\n"):
          stdout.write("\n")

      # Display error if any
      if result.error:
        stdout.write("ERROR:\n")
        stdout.write(result.error)
        stdout.write("\n")

      # Report success/failure
      if not result.success:
        stdout.write("Execution failed\n")
    except Exception as e:
      raise E(f"Failed to execute code: {str(e)}")

  elif action == "delete":
    # Session ID/name is required for delete
    session_ref = get_kwarg("session")

    try:
      # Delete the session
      success = api.delete_session(session_ref)
      if success:
        stdout.write(f"Session '{session_ref}' deleted successfully\n")
      else:
        stdout.write(f"Session '{session_ref}' not found or could not be deleted\n")
    except Exception as e:
      raise E(f"Failed to delete session: {str(e)}")

  else:
    raise E(f"Unknown session action: {action}")

def handle_interpreter_kernel(
  pop_arg: Callable[[str], str],
  get_kwarg: Callable[[str, Union[str, bool, Any]], str],
  env: dict[str, str],
  stdin: TextIO,
  stdout: TextIO,
  kwargs: dict[str, str],
  remainder: Deque[str],
  E: type[Exception],
):
  """
  Handle the 'interpreter kernel' subcommand.
  
  Supports the following actions:
  - create: Create a new kernel in a session
  - list: List kernels (all or in a specific session)
  - execute: Execute code in a kernel
  - interrupt: Interrupt a running kernel
  - restart: Restart a kernel
  - delete: Delete a kernel
  
  Examples:
    python -m DevAgent interpreter kernel create --session=dev_session --name=python_kernel
    python -m DevAgent interpreter kernel list --session=dev_session
    python -m DevAgent interpreter kernel execute --ref=dev_session/python_kernel --code="print('hello')"
    python -m DevAgent interpreter kernel restart --ref=dev_session/python_kernel
  """
  # Get the kernel action
  try:
    action = pop_arg("action")
  except Exception:
    # Show usage if no action provided
    stdout.write("Usage: python -m DevAgent interpreter kernel <action> [options]\n")
    stdout.write("Actions: create, list, execute, interrupt, restart, delete\n")
    return

  # Get base directory from kwargs or use current directory
  try:
    base_dir = get_kwarg("dir")
    base_dir_path = pathlib.Path(base_dir)
  except:
    base_dir_path = pathlib.Path(os.getcwd()) / '.devagent'

  # Create the API instance
  api = InterpreterAPI(base_dir_path)

  # Handle different kernel actions
  if action == "create":
    # Get required session reference and optional kernel name
    session_ref = get_kwarg("session")
    
    try:
      kernel_name = get_kwarg("name", "main")
    except:
      kernel_name = "main"
      
    try:
      kernel_type = get_kwarg("type", "python3")
    except:
      kernel_type = "python3"

    try:
      # Create a kernel in the session
      kernel = api.create_kernel(session_ref, kernel_name, kernel_type=kernel_type)
      stdout.write(f"Kernel created: {kernel_name}\n")
      stdout.write(f"Kernel ID: {kernel.id}\n")
      stdout.write(f"Kernel Type: {kernel_type}\n")
      stdout.write(f"In Session: {session_ref}\n")
    except Exception as e:
      raise E(f"Failed to create kernel: {str(e)}")

  elif action == "list":
    try:
      # Get optional session reference
      try:
        session_ref = get_kwarg("session")
        session_specified = True
      except:
        session_specified = False
      
      if session_specified:
        # List kernels in a specific session
        session = api.get_session(session_ref)
        if not session:
          raise E(f"Session '{session_ref}' not found")
        
        kernels = session.list_kernels()
        if kernels:
          stdout.write(f"Kernels in session '{session_ref}':\n")
          for kernel in kernels:
            status = "alive" if kernel.get("alive", False) else "dead"
            stdout.write(f"  {kernel['name']} (ID: {kernel['id']}, Type: {kernel.get('kernel_type', 'unknown')}, Status: {status})\n")
        else:
          stdout.write(f"No kernels in session '{session_ref}'\n")
      else:
        # List all kernels across all sessions
        kernels = api.list_kernels()
        if kernels:
          stdout.write("All kernels:\n")
          for kernel in kernels:
            status = "alive" if kernel.get("alive", False) else "dead"
            session_id = kernel.get("session_id", "unknown")
            stdout.write(f"  {kernel['name']} (ID: {kernel['id']}, Session: {session_id}, Type: {kernel.get('kernel_type', 'unknown')}, Status: {status})\n")
        else:
          stdout.write("No kernels found\n")
    except Exception as e:
      raise E(f"Failed to list kernels: {str(e)}")

  elif action == "execute":
    # Get required kernel reference and code
    kernel_ref = get_kwarg("ref")
    code = get_kwarg("code")

    try:
      # Execute the code
      result = api.execute_code(kernel_ref, code)

      # Display output
      if result.stdout:
        stdout.write(result.stdout)
        # Add newline if not already present
        if not result.stdout.endswith("\n"):
          stdout.write("\n")

      # Display error if any
      if result.error:
        stdout.write("ERROR:\n")
        stdout.write(result.error)
        stdout.write("\n")

      # Report success/failure
      if not result.success:
        stdout.write("Execution failed\n")
    except Exception as e:
      raise E(f"Failed to execute code: {str(e)}")

  elif action == "interrupt":
    # Get required kernel reference
    kernel_ref = get_kwarg("ref")

    try:
      # Get the kernel
      kernel = api.get_kernel(kernel_ref)
      if not kernel:
        raise E(f"Kernel '{kernel_ref}' not found")
      
      # Interrupt the kernel
      success = kernel.interrupt()
      if success:
        stdout.write(f"Kernel '{kernel_ref}' interrupted successfully\n")
      else:
        stdout.write(f"Failed to interrupt kernel '{kernel_ref}'\n")
    except Exception as e:
      raise E(f"Failed to interrupt kernel: {str(e)}")

  elif action == "restart":
    # Get required kernel reference
    kernel_ref = get_kwarg("ref")

    try:
      # Get the kernel
      kernel = api.get_kernel(kernel_ref)
      if not kernel:
        raise E(f"Kernel '{kernel_ref}' not found")
      
      # Restart the kernel
      success = kernel.restart()
      if success:
        stdout.write(f"Kernel '{kernel_ref}' restarted successfully\n")
      else:
        stdout.write(f"Failed to restart kernel '{kernel_ref}'\n")
    except Exception as e:
      raise E(f"Failed to restart kernel: {str(e)}")

  elif action == "delete":
    # Get required kernel reference
    kernel_ref = get_kwarg("ref")

    try:
      # Delete the kernel
      success = api.delete_kernel(kernel_ref)
      if success:
        stdout.write(f"Kernel '{kernel_ref}' deleted successfully\n")
      else:
        stdout.write(f"Failed to delete kernel '{kernel_ref}'\n")
    except Exception as e:
      raise E(f"Failed to delete kernel: {str(e)}")

  else:
    raise E(f"Unknown kernel action: {action}")

def handle_interpreter(
  pop_arg: Callable[[str], str],
  get_kwarg: Callable[[str, Union[str, bool, Any]], str],
  env: dict[str, str],
  stdin: TextIO,
  stdout: TextIO,
  kwargs: dict[str, str],
  remainder: deque[str],
  E: type[Exception],
):
  """Handle the 'interpreter' subcommand with its operations.
  
  Supports the following operations:
  - session: Manage computation sessions
  - kernel: Manage computation kernels
  
  Examples:
    python -m DevAgent interpreter session create --name=dev_session
    python -m DevAgent interpreter session list
    python -m DevAgent interpreter kernel create --session=dev_session --name=main
    python -m DevAgent interpreter kernel execute --ref=dev_session/main --code="print('hello')"
  """

  # Get the interpreter operation (e.g., "session", "kernel")
  op = pop_arg("operation")

  if op == "session":
    handle_interpreter_session(pop_arg, get_kwarg, env, stdin, stdout, kwargs, remainder, E)
  elif op == "kernel":
    handle_interpreter_kernel(pop_arg, get_kwarg, env, stdin, stdout, kwargs, remainder, E)
  else:
    raise E(f"Unknown interpreter operation: {op}")

def main(
  args: deque[str],
  kwargs: dict[str, str],
  remainder: deque[str],
  env: dict[str, str],
  stdin: TextIO,
  stdout: TextIO,
) -> bool:

  class E(Exception):
    ...

  # Function to pop and return the next argument from args queue
  def _pop_arg(name: str) -> str:
    """Pop the next argument from the args queue or raise an exception if empty.

        Args:
            name: Name of the argument for error reporting

        Returns:
            The next argument value

        Raises:
            E: If no more arguments are available
        """
    try:
      return args.popleft()
    except IndexError:
      raise E(f"missing positional arg: `{name.upper()}`")

  NO_DEFAULT = type("NO_DEFAULT", (), {})

  # Function to get a keyword argument with optional default value
  def _get_kwarg(k: str, default: Union[str, bool, type[NO_DEFAULT]] = NO_DEFAULT) -> str:
    """Get a keyword argument or return default if provided.

        Args:
            k: Keyword argument name
            default: Default value to return if not found, or NO_DEFAULT to require the argument

        Returns:
            The keyword argument value

        Raises:
            E: If the argument is required but not found
        """
    assert default is NO_DEFAULT or isinstance(default, (str, bool))
    try:
      return kwargs.get(k, default) if default is not NO_DEFAULT else kwargs[k]
    except KeyError:
      raise E(f"Missing Expected Flag: `--{k}`")

  try:
    subcmd = _pop_arg("subcmd")

    if subcmd == "ontology":
      handle_ontology(
        _pop_arg,
        _get_kwarg,
        env,
        stdin,
        stdout,
        kwargs,
        remainder,
        E,
      )
    elif subcmd == "interpreter":
      handle_interpreter(
        _pop_arg,
        _get_kwarg,
        env,
        stdin,
        stdout,
        kwargs,
        remainder,
        E,
      )
    else:
      raise E(f"Unknown subcommand: {subcmd}")

  except E as e:
    logger.info("CLI Error", exc_info=True)
    logger.critical(str(e))
    return False
  return True

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
        yield True # Any CLI Exceptions will be raised here
    except:
      logger.critical("Unhandled Exception", exc_info=True)
    finally:
      logger.debug("fin")
      logging.shutdown()
      sys.stdout.flush()
      sys.stderr.flush()

  @classmethod
  def parse_flag(cls, flag: str) -> tuple[str, str]:
    assert flag.startswith("-")
    if "=" in flag:
      return flag.lstrip("-").split("=", maxsplit=1)
    else:
      return flag.lstrip("-"), True

  @classmethod
  def parse_argv(cls, argv: list[str]) -> tuple[deque[str], dict[str, str], deque[str]]:
    """Parses Argv returning ( args, kwargs, remainder )"""
    remainder = []
    if "--" in argv:
      idx = argv.index("--")
      remainder = argv[idx + 1:]
      argv = argv[:idx]
    logger.debug(f"{remainder=}")

    args = deque(a for a in argv if not a.startswith("-"))
    logger.debug(f"{args=}")
    flags = dict(CLI.parse_flag(f) for f in argv if f.startswith("-"))
    logger.debug(f"{flags=}")
    return (args, flags, deque(remainder))

if __name__ == "__main__":
  RC = 2
  with CLI.session() as _ok:
    if _ok:
      RC = (0 if main(
        *CLI.parse_argv(sys.argv[1:]),
        dict(os.environ),
        sys.stdin,
        sys.stdout,
      ) else 1)
  exit(RC)
