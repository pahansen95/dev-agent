"""

The Package Entrypoint

"""
from __future__ import annotations
from typing import *
from collections.abc import *
from types import *

import logging, os, sys, contextlib, pathlib
from collections import deque

SCRIPT = pathlib.Path(__file__)
CONTEXT = SCRIPT.parent # The context of Script
logger = logging.getLogger(__package__ if __name__ == '__main__' else __name__)

def main(
  args: deque[str],
  kwargs: dict[str, str],
  remainder: deque[str],
  env: dict[str, str],
  stdin: TextIO,
  stdout: TextIO,
) -> bool:

  class E(Exception): ...

  def _pop_arg(name: str) -> str:
    try: return args.popleft()
    except IndexError: raise E(f'missing positional arg: `{name.upper()}`')
  NO_DEFAULT = type('NO_DEFAULT', (), {})
  def _get_kwarg(k: str, default: str | bool | type[NO_DEFAULT] = NO_DEFAULT) -> str:
    assert default is NO_DEFAULT or isinstance(default, (str, bool))
    try: return kwargs.get(k, default) if default is not NO_DEFAULT else kwargs[k]
    except KeyError: raise E(f'Missing Expected Flag: `--{k}`')

  try:

    subcmd = _pop_arg('subcmd')

    if subcmd == 'foo':

      try: ... # TODO
      except Exception as e: raise E('Failed to FOO') from e

    elif subcmd == 'bar':

      try: ... # TODO
      except Exception as e: raise E('Failed to BAR') from e

    else: raise E(f'Unknown Subcommand: {subcmd}')

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
  