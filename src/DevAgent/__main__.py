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
logger = logging.getLogger(__package__ if __name__ == '__main__' else __name__)

def handle_ontology(
  pop_arg: Callable[[str], str],
  get_kwarg: Callable[[str, Union[str, bool, Any]], str],
  env: dict[str, str],
  stdin: TextIO,
  stdout: TextIO,
  stderr: TextIO,
  kwargs: dict[str, str],
  remainder: deque[str],
  E: type[Exception],
):
  op = pop_arg('operation')  # e.g. "init", "info", "dump", "add-node", "add-edge"
  # support both "init" and "create" as synonyms if you like
  in_f  = get_kwarg('f', '-')  # input JSON file (or '-' for stdin)
  out_f = get_kwarg('o', '-')  # output file

  graph = (None if op in ('init','create')
       else OntologyAPI.load(json.load(open(in_f) if in_f!='-' else stdin)))

  match op:
    case 'init' | 'create':
      graph = OntologyAPI.init()
    case 'info':
      n, e = OntologyAPI.info(graph)
      stdout.write(f"nodes={n} edges={e}\n"); return
    case 'dump':
      json.dump(OntologyAPI.dump(graph),
            open(out_f,'w') if out_f!='-' else stdout,
            indent=2)
      return
    case 'add-node':
      id_, lbl = pop_arg('ID'), pop_arg('LABEL')
      kind  = kwargs.get('kind','concept')
      meta  = json.loads(kwargs.get('meta','{}'))
      OntologyAPI.add_node(graph, id_, lbl, kind, meta)
    case 'add-edge':
      src, rel, dst = (pop_arg(k) for k in ('SRC','REL','DST'))
      OntologyAPI.add_edge(graph, src, rel, dst)
    case _:
      raise E(f"Unknown ontology operation: {op}")

  # for mutating ops we write back the updated graph
  json.dump(OntologyAPI.dump(graph),
        open(out_f,'w') if out_f!='-' else stdout,
        indent=2)
  stdout.write('\n')

def main(
  args: deque[str],
  kwargs: dict[str, str],
  remainder: deque[str],
  env: dict[str, str],
  stdin: TextIO,
  stdout: TextIO,
) -> bool:

  class E(Exception): ...

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
    try: return args.popleft()
    except IndexError: raise E(f'missing positional arg: `{name.upper()}`')
  
  NO_DEFAULT = type('NO_DEFAULT', (), {})
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
    try: return kwargs.get(k, default) if default is not NO_DEFAULT else kwargs[k]
    except KeyError: raise E(f'Missing Expected Flag: `--{k}`')

  try:
    subcmd = _pop_arg('subcmd')

    if subcmd == 'ontology': 
      handle_ontology(_pop_arg, _get_kwarg, env, stdin, stdout, sys.stderr, kwargs, remainder, E)
    elif subcmd == 'interpreter': 
      handle_interpreter(_pop_arg, _get_kwarg, env, stdin, stdout, sys.stderr, kwargs, remainder, E)
    else: 
      raise E(f"Unknown subcommand: {subcmd}")

  except E as e:
    logger.info('CLI Error', exc_info=True)
    logger.critical(str(e))
    return False
  return True

class CLI:

  @classmethod
  @contextlib.contextmanager
  def session(cls):
    try:
      try:
        logging.basicConfig(stream=sys.stderr, level=os.environ.get('LOG_LEVEL', 'INFO'))
      except Exception as e:
        logging.basicConfig(stream=sys.stderr, level='INFO')
        logger.critical(f'Bad Log Configuration: {e}')
        yield False
      else:
        logger.debug('inizio')
        yield True # Any CLI Exceptions will be raised here
    except:
      logger.critical('Unhandled Exception', exc_info=True)
    finally:
      logger.debug('fin')
      logging.shutdown()
      sys.stdout.flush()
      sys.stderr.flush()
  
  @classmethod
  def parse_flag(cls, flag: str) -> tuple[str, str]:
    assert flag.startswith('-')
    if '=' in flag: return flag.lstrip('-').split('=', maxsplit=1)
    else: return flag.lstrip('-'), True

  @classmethod
  def parse_argv(cls, argv: list[str]) -> tuple[deque[str], dict[str, str], deque[str]]:
    """Parses Argv returning ( args, kwargs, remainder )"""
    remainder = []
    if '--' in argv:
      idx = argv.index('--')
      remainder = argv[idx+1:]
      argv = argv[:idx]
    logger.debug(f'{remainder=}')

    args = deque(a for a in argv if not a.startswith('-'))
    logger.debug(f'{args=}')
    flags = dict(CLI.parse_flag(f) for f in argv if f.startswith('-'))
    logger.debug(f'{flags=}')
    return (args, flags, deque(remainder))

if __name__ == "__main__":
  RC = 2
  with CLI.session() as _ok:
    if _ok: RC = 0 if main(
      *CLI.parse_argv(sys.argv[1:]),
      dict(os.environ),
      sys.stdin,
      sys.stdout,
    ) else 1
  exit(RC)