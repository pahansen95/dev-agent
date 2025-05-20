"""

A Source File that feeds the Knowledge Base

"""
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SourceDocument:
  path: Path