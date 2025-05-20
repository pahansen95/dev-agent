"""

Outward functionality of the KB Artifact including Generation & Rendering

"""
import pathlib, logging
from ._core.artifact import KnowledgeTree
from ._core.source import SourceDocument

logger = logging.getLogger(__name__)

class CLI:
  """A Namespace Implementing the CLI Interface for this Module"""

  @staticmethod
  def generate(
    max_iter: int = None,
  ):
    """Iteratively generates a KB Artifact"""

    docs: list[SourceDocument] = [ ... ] # TODO: Read the Docs
    kb_artif: KnowledgeTree = ... # TODO: Load the Artifact

    iter_idx = 0
    while True:
      logger.info(f'Starting Information Extraction for {kb_artif}')
      # Iteratively Extract Information from the Source Documentation & incorporate it into the KB Artifact
      for doc in docs:
        logger.info(f'Extracting Information from {doc}')
        for chunk_idx, chunk in enumerate(doc.split()): # TODO: How do we split the document?
          logger.debug(f'Chunk {chunk_idx}')
          information = ... # TODO: Extract relevant information from the chunk
          if information is None: # Nothing relevant found
            continue
          kb_artif.insert(
            information,
            ... # TODO: Where do we insert it?
          )

      # Iteratation Control
      if max_iter is None: # Interactive
        if not input('continue? [y/n] ').lower().strip().startswith('y'): # TODO: Better handling
          break
      else: # Non-Interactive
        assert isinstance(max_iter, int)
        if iter_idx > max_iter: break

  @staticmethod
  def entrypoint(*args, **kwds):
    subcmd = ...

if __name__ == '__main__':
  CLI.entrypoint()
