"""

Centralized Configuration

"""
from dataclasses import dataclass

@dataclass
class LogConfig:
  """Logging Configuration"""

@dataclass
class KBConfig:
  """Knowlege Base Configuration"""

@dataclass
class AzureOAIConfig:
  """Azure Provider Config"""

@dataclass
class OpenAIConfig:
  """OpenAI Provider Config"""

@dataclass
class LLMConfig:
  """LLM Config"""

@dataclass
class AppConfig:
  """Application wide configuration"""
  log: LogConfig
  kb: KBConfig
  provider: AzureOAIConfig | OpenAIConfig
  llm: LLMConfig

