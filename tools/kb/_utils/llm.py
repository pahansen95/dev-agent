"""

Protocols & Types for LLMs

"""
from typing import Protocol, Literal
from dataclasses import dataclass
from . import http

@dataclass
class Message:
  role: Literal['user', 'developer', 'assistant']
  content: str

class LLM(Protocol):
  def chat(self, *msg: Message) -> Message:
    """Chat with a model providing a sequence of input messages"""
    ...

@dataclass
class AzureOAI(LLM):
  
  def chat(self, *msg: Message) -> Message: raise NotImplementedError