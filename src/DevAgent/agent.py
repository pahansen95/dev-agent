"""DevAgent Agent implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generator, Tuple, Optional

from .interpreter import get_client

@dataclass
class Context:

  """The Agent's immediate ephemeral context."""

  content: str = field(default="")

@dataclass
class Agent:

  """An autonomous agent executing code via a Jupyter kernel."""

  def __init__(self, kernel_name: str, transport: str = "zmq"):
    """
        Initialize the agent with a connection to a remote kernel.

        Parameters
        ----------
        kernel_name : str
          Name of the kernel instance (directory under .kernels).
        transport : str
          'zmq' for ZeroMQ transport, 'http' for HTTP/WebSocket.
        """
    self.client = get_client(kernel_name, transport)
    self.ctx = Context()

  def repl(self) -> Generator[tuple[str, Optional[str]], str | None, None]:
    """
        Generator that receives code statements sent in and yields (output, error).

        Usage:
          agent = Agent('dev')
          repl = agent.repl()
          next(repl)  # prime the generator
          output, error = runner.send("print('hello')")
        """
    _ = yield # Prime the generator
    assert _ is None
    code: str = yield # wait for the first code statement
    assert code is not None

    while code is not None:
      # Send code to the kernel
      msg_id = self.client.execute(code)

      # Collect output and errors
      output: str = ""
      error: Optional[str] = None

      while True:
        msg = self.client.get_iopub_msg(timeout=1)
        msg_type = msg["msg_type"]
        content = msg["content"]

        if msg_type == "stream":
          output += content.get("text", "")
        elif msg_type == "error":
          error = "".join(content.get("traceback", []))
        elif msg_type == "execute_reply":
          # Execution finished
          break

      # Yield the results and wait for next code
      code = yield (output, error)
