"""
The Package Entrypoint

"""

from __future__ import annotations
from typing import *
from collections.abc import *
from types import *
from typing import Callable, Union, Any

import logging, os, sys, contextlib, pathlib, json
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

def handle_interpreter_server(
  pop_arg: Callable[[str], str],
  get_kwarg: Callable[[str, Union[str, bool, Any]], str],
  env: dict[str, str],
  stdin: TextIO,
  stdout: TextIO,
  kwargs: dict[str, str],
  remainder: deque[str],
  E: type[Exception],
):
  """Handle the 'interpreter server' subcommand.
  
  Supports the following actions:
  - up: Start the Jupyter server
  - down: Stop the Jupyter server
  - status: Check server status
  - purge: Stop and remove server state
  
  Examples:
    python -m DevAgent interpreter server up
    python -m DevAgent interpreter server up --url=tcp://localhost:8888
    python -m DevAgent interpreter server status
  """
  # Get the server action (e.g., "up", "down", "status", "purge")
  try:
    action = pop_arg("action")
  except Exception:
    # Show usage if no action provided
    stdout.write("Usage: python -m DevAgent interpreter server <action> [options]\n")
    stdout.write("Actions: up, down, status, purge\n")
    return

  # Get base directory from kwargs or use current directory
  try:
    base_dir = get_kwarg("dir")
  except:
    base_dir = os.path.join(os.getcwd(), '.devagent')

  # Create the API instance
  from .api import InterpreterServerAPI
  api = InterpreterServerAPI.factory(base_dir)

  # Handle different server actions
  if action == "up":
    server_url = kwargs.get("url")
    try:
      conn_info = api.up(server_url)
      stdout.write(f"Server started successfully\n")
      stdout.write(f"URI: {conn_info['uri']}\n")
    except Exception as e:
      raise E(f"Failed to start server: {str(e)}")

  elif action == "down":
    result = api.down()
    if result:
      stdout.write("Server stopped successfully\n")
    else:
      stdout.write("Server was not running\n")

  elif action == "status":
    status = api.status()
    stdout.write(f"Server status: {'Running' if status['running'] else 'Not running'}\n")
    if status['running']:
      stdout.write(f"PID: {status['pid']}\n")
      stdout.write(f"URI: {status['connection_info']['uri']}\n")
      import time
      started = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['last_start_time']))
      stdout.write(f"Started: {started}\n")

  elif action == "purge":
    result = api.purge()
    if result:
      stdout.write("Server purged successfully\n")
    else:
      stdout.write("Failed to purge server\n")

  else:
    raise E(f"Unknown server action: {action}")

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
  - interrupt: Interrupt execution in a session
  - restart: Restart a session's kernel
  - delete: Delete a session
  
  Examples:
    python -m DevAgent interpreter session create
    python -m DevAgent interpreter session create --id=dev_session
    python -m DevAgent interpreter session list
    python -m DevAgent interpreter session execute --code="print('hello')" --session=dev_session
  """
  # Get the session action
  try:
    action = pop_arg("action")
  except Exception:
    # Show usage if no action provided
    stdout.write("Usage: python -m DevAgent interpreter session <action> [options]\n")
    stdout.write("Actions: create, list, execute, interrupt, restart, delete\n")
    return

  # Get base directory from kwargs or use current directory
  try:
    base_dir = get_kwarg("dir")
  except:
    base_dir = os.path.join(os.getcwd(), '.devagent')

  # Create the API instance
  api = InterpreterSessionAPI(base_dir)

  # Handle different session actions
  if action == "create":
    # Get optional session ID and kernel name
    try:
      session_id = get_kwarg("id", "main")
    except:
      session_id = "main"

    try:
      kernel_name = get_kwarg("kernel", "python3")
    except:
      kernel_name = "python3"

    try:
      # Create the session
      result = api.create_session(session_id, kernel_name)
      if result.get("success", True): # Default to True if success not present
        stdout.write(f"Session created: {result['id']}\n")
        stdout.write(f"Kernel name: {result.get('kernel_name', kernel_name)}\n")
        stdout.write(f"Session directory: {result.get('session_dir', 'unknown')}\n")
      else:
        stdout.write(f"Failed to create session: {result.get('error', 'Unknown error')}\n")
    except Exception as e:
      raise E(f"Failed to create session: {str(e)}")

  elif action == "list":
    try:
      # List active sessions
      sessions = api.list_sessions()
      if sessions:
        stdout.write("Active sessions:\n")
        for session in sessions:
          kernel_status = "alive" if session.get("kernel_alive", False) else "dead"
          kernel_name = session.get("kernel_name", "unknown")
          stdout.write(f"  {session['id']} (kernel: {kernel_name}, status: {kernel_status})\n")
      else:
        stdout.write("No active sessions\n")
    except Exception as e:
      raise E(f"Failed to list sessions: {str(e)}")

  elif action == "execute":
    # Get required code and optional session ID
    code = get_kwarg("code")

    try:
      session_id = get_kwarg("session", "main")
    except:
      session_id = "main"

    try:
      outfile = get_kwarg("outfile")
      use_outfile = True
    except:
      use_outfile = False

    try:
      # Execute the code
      result = api.execute(code, session_id)

      if use_outfile:
        # Write results to file
        with open(outfile, "w") as f:
          if result.get("stdout"):
            f.write(result["stdout"])
          if result.get("error"):
            f.write("\nERROR:\n")
            f.write(result["error"])
        stdout.write(f"Results written to {outfile}\n")
      else:
        # Write results to stdout
        if result.get("stdout"):
          stdout.write(result["stdout"])
          # Add newline if not already present
          if result["stdout"] and not result["stdout"].endswith("\n"):
            stdout.write("\n")

        if result.get("error"):
          stdout.write("ERROR:\n")
          stdout.write(result["error"])
          stdout.write("\n")

      # Report execution time if available
      if "execution_time" in result:
        stdout.write(f"Execution time: {result['execution_time']:.3f} seconds\n")

      # Report success/failure
      if not result.get("success", False):
        stdout.write("Execution failed\n")
    except Exception as e:
      raise E(f"Failed to execute code: {str(e)}")

  elif action == "interrupt":
    try:
      session_id = get_kwarg("session", "main")
    except:
      session_id = "main"

    try:
      # Interrupt the session
      result = api.interrupt(session_id)
      if result.get("success", False):
        stdout.write(f"Session {session_id} interrupted successfully\n")
      else:
        stdout.write(f"Failed to interrupt session {session_id}: {result.get('error', 'Unknown error')}\n")
    except Exception as e:
      raise E(f"Failed to interrupt session: {str(e)}")

  elif action == "restart":
    try:
      session_id = get_kwarg("session", "main")
    except:
      session_id = "main"

    try:
      # Restart the session
      result = api.restart(session_id)
      if result.get("success", False):
        stdout.write(f"Session {session_id} restarted successfully\n")
      else:
        stdout.write(f"Failed to restart session {session_id}: {result.get('error', 'Unknown error')}\n")
    except Exception as e:
      raise E(f"Failed to restart session: {str(e)}")

  elif action == "delete":
    # Session ID is required for delete
    session_id = get_kwarg("session")

    try:
      # Delete the session
      result = api.delete_session(session_id)
      if result.get("success", False):
        stdout.write(f"Session {session_id} deleted successfully\n")
      else:
        stdout.write(f"Failed to delete session {session_id}: {result.get('error', 'Session not found')}\n")
    except Exception as e:
      raise E(f"Failed to delete session: {str(e)}")

  else:
    raise E(f"Unknown session action: {action}")

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
  - server: Manage the Jupyter server (up, down, status, purge)
  - kernel: Manage kernels (to be implemented)
  
  Examples:
    python -m DevAgent interpreter server up
    python -m DevAgent interpreter server status
    python -m DevAgent interpreter session list
  """

  # Get the interpreter operation (e.g., "server")
  op = pop_arg("operation")

  if op == "server":
    handle_interpreter_server(pop_arg, get_kwarg, env, stdin, stdout, kwargs, remainder, E)
  elif op == "session":
    handle_interpreter_session(pop_arg, get_kwarg, env, stdin, stdout, kwargs, remainder, E)
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
