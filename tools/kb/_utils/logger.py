"""
# Knowledge Base Generator - Logging Utility

A centralized logging facility for the Knowledge Base Generator tool that provides
consistent logging interfaces with configurable verbosity and output destinations.

This module handles:
- Log level configuration (ERROR, WARNING, INFO, DEBUG, TRACE)
- Contextual logging with metadata (timestamp, module, function, line)
- Structured log formatting for easier parsing
- Multiple output destinations (console, file)
- Correlation tracking across operations
"""

import logging
import os
import sys
import json
import inspect
import datetime
import threading
from enum import IntEnum
from typing import Any, Dict, Optional, Union, cast

# -----------------------------------------------------------------------------
# Custom Log Levels
# -----------------------------------------------------------------------------

# Add TRACE level (even more detailed than DEBUG)
TRACE_LEVEL = 5 # Lower than DEBUG (10)
logging.addLevelName(TRACE_LEVEL, "TRACE")

class LogLevel(IntEnum):

  """Enum for log levels with easy comparison."""
  TRACE = TRACE_LEVEL
  DEBUG = logging.DEBUG
  INFO = logging.INFO
  WARNING = logging.WARNING
  ERROR = logging.ERROR
  CRITICAL = logging.CRITICAL

# -----------------------------------------------------------------------------
# Logging Context
# -----------------------------------------------------------------------------

class LogContext:

  """Thread-local storage for logging context data."""

  _local = threading.local()

  @classmethod
  def get_correlation_id(cls) -> str:
    """Get the current correlation ID or generate a new one."""
    if not hasattr(cls._local, 'correlation_id'):
      cls._local.correlation_id = f"kb-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{threading.get_ident()}"
    return cls._local.correlation_id

  @classmethod
  def set_correlation_id(cls, correlation_id: str) -> None:
    """Set a custom correlation ID."""
    cls._local.correlation_id = correlation_id

  @classmethod
  def get_context(cls) -> Dict[str, Any]:
    """Get the full logging context."""
    context = {'correlation_id': cls.get_correlation_id(), 'thread_id': threading.get_ident()}
    # Add any additional context that's been set
    if hasattr(cls._local, 'additional_context'):
      context.update(cls._local.additional_context)
    return context

  @classmethod
  def add_context(cls, key: str, value: Any) -> None:
    """Add a key-value pair to the logging context."""
    if not hasattr(cls._local, 'additional_context'):
      cls._local.additional_context = {}
    cls._local.additional_context[key] = value

  @classmethod
  def clear_context(cls) -> None:
    """Clear all context data except correlation ID."""
    if hasattr(cls._local, 'additional_context'):
      del cls._local.additional_context

# -----------------------------------------------------------------------------
# Custom Formatter
# -----------------------------------------------------------------------------

class StructuredFormatter(logging.Formatter):

  """Formatter that outputs logs in a structured format (JSON or text)."""

  def __init__(self, use_json: bool = False, include_context: bool = True):
    """
        Initialize the formatter.
        
        Args:
            use_json: Whether to output logs as JSON
            include_context: Whether to include context information
        """
    super().__init__()
    self.use_json = use_json
    self.include_context = include_context

  def format(self, record: logging.LogRecord) -> str:
    """Format the log record."""
    # Extract the caller information
    frame = inspect.currentframe()
    # Walk up the stack to find the non-logging caller
    while frame:
      if frame.f_code.co_filename != __file__:
        break
      frame = frame.f_back

    # Prepare the log data
    log_data = {
      'timestamp': self.formatTime(record, '%Y-%m-%d %H:%M:%S.%f'),
      'level': record.levelname,
      'message': record.getMessage(),
      'module': record.module,
      'function': record.funcName,
      'line': record.lineno
    }

    # Add exception info if present
    if record.exc_info:
      log_data['exception'] = {'type': record.exc_info[0].__name__, 'message': str(record.exc_info[1]), 'traceback': self.formatException(record.exc_info)}

    # Add context information if available
    if self.include_context:
      log_data.update(LogContext.get_context())

    # Format as JSON or text
    if self.use_json:
      return json.dumps(log_data)
    else:
      # Format as text for console readability
      basic = f"[{log_data['timestamp']}] {log_data['level']:8} {log_data['module']}.{log_data['function']}:{log_data['line']} - {log_data['message']}"

      # Add correlation ID if available
      if 'correlation_id' in log_data:
        basic = f"{basic} (correlation_id: {log_data['correlation_id']})"

      # Add exception info
      if 'exception' in log_data:
        exc_info = log_data['exception']
        basic = f"{basic}\n    {exc_info['type']}: {exc_info['message']}\n{exc_info['traceback']}"

      return basic

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------

class LoggerConfig:

  """Configuration for the KB Generator logger."""

  DEFAULT_LEVEL = LogLevel.INFO
  DEFAULT_FORMAT = "text" # or "json"
  DEFAULT_OUTPUT = "console" # or "file" or "both"
  DEFAULT_FILENAME = "kb_generator.log"

  @classmethod
  def get_level_from_env(cls) -> int:
    """Get log level from environment variable."""
    level_name = os.environ.get('KB_LOG_LEVEL', '').upper()
    if level_name:
      try:
        return LogLevel[level_name]
      except KeyError:
        print(f"Warning: Invalid log level '{level_name}'. Using default ({cls.DEFAULT_LEVEL.name}).")
    return cls.DEFAULT_LEVEL

  @classmethod
  def get_format_from_env(cls) -> str:
    """Get log format from environment variable."""
    format_name = os.environ.get('KB_LOG_FORMAT', '').lower()
    if format_name in ('json', 'text'):
      return format_name
    return cls.DEFAULT_FORMAT

  @classmethod
  def get_output_from_env(cls) -> str:
    """Get log output destination from environment variable."""
    output_name = os.environ.get('KB_LOG_OUTPUT', '').lower()
    if output_name in ('console', 'file', 'both'):
      return output_name
    return cls.DEFAULT_OUTPUT

  @classmethod
  def get_filename_from_env(cls) -> str:
    """Get log filename from environment variable."""
    return os.environ.get('KB_LOG_FILENAME', cls.DEFAULT_FILENAME)

# -----------------------------------------------------------------------------
# KB Generator Logger
# -----------------------------------------------------------------------------

class KBLogger:

  """Main logger for the KB Generator tool."""

  _loggers: Dict[str, logging.Logger] = {}
  _initialized = False

  @classmethod
  def initialize(
      cls, level: Optional[Union[int, str]] = None, format_type: Optional[str] = None, output: Optional[str] = None, filename: Optional[str] = None) -> None:
    """
        Initialize the logging system.
        
        Args:
            level: Log level (name or value)
            format_type: Log format ('json' or 'text')
            output: Output destination ('console', 'file', or 'both')
            filename: Log file name (only used if output is 'file' or 'both')
        """
    if cls._initialized:
      return

    # Get configuration
    if level is None:
      level = LoggerConfig.get_level_from_env()
    elif isinstance(level, str):
      try:
        level = LogLevel[level.upper()]
      except KeyError:
        print(f"Warning: Invalid log level '{level}'. Using default ({LoggerConfig.DEFAULT_LEVEL.name}).")
        level = LoggerConfig.DEFAULT_LEVEL

    format_type = format_type or LoggerConfig.get_format_from_env()
    output = output or LoggerConfig.get_output_from_env()
    filename = filename or LoggerConfig.get_filename_from_env()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
      root_logger.removeHandler(handler)

    # Create formatter
    use_json = format_type == 'json'
    formatter = StructuredFormatter(use_json=use_json)

    # Add console handler if needed
    if output in ('console', 'both'):
      console_handler = logging.StreamHandler(sys.stdout)
      console_handler.setFormatter(formatter)
      root_logger.addHandler(console_handler)

    # Add file handler if needed
    if output in ('file', 'both'):
      file_handler = logging.FileHandler(filename)
      file_handler.setFormatter(formatter)
      root_logger.addHandler(file_handler)

    cls._initialized = True

  @classmethod
  def get_logger(cls, name: str) -> logging.Logger:
    """
        Get a logger for a specific module.
        
        Args:
            name: The module name
            
        Returns:
            A configured logger instance
        """
    if not cls._initialized:
      cls.initialize()

    if name not in cls._loggers:
      logger = logging.getLogger(name)

      # Add trace method to logger
      def trace(msg, *args, **kwargs):
        if logger.isEnabledFor(TRACE_LEVEL):
          logger._log(TRACE_LEVEL, msg, args, **kwargs)

      logger.trace = trace # type: ignore
      cls._loggers[name] = logger

    return cls._loggers[name]

# -----------------------------------------------------------------------------
# Convenience Functions
# -----------------------------------------------------------------------------

def get_logger(name: str = None) -> logging.Logger:
  """
    Get a logger for the calling module.
    
    Args:
        name: Optional module name (auto-detected if not provided)
        
    Returns:
        A configured logger instance
    """
  if name is None:
    # Auto-detect the calling module name
    frame = inspect.currentframe()
    if frame:
      frame = frame.f_back
      if frame:
        module = inspect.getmodule(frame)
        if module:
          name = module.__name__

  if not name:
    name = 'kb'

  return KBLogger.get_logger(name)

def configure_logging(
    level: Optional[Union[int, str]] = None, format_type: Optional[str] = None, output: Optional[str] = None, filename: Optional[str] = None) -> None:
  """
    Configure the KB Generator logging system.
    
    Args:
        level: Log level (name or value)
        format_type: Log format ('json' or 'text')
        output: Output destination ('console', 'file', or 'both')
        filename: Log file name (only used if output is 'file' or 'both')
    """
  KBLogger.initialize(level, format_type, output, filename)

def set_correlation_id(correlation_id: str) -> None:
  """
    Set a custom correlation ID for the current thread.
    
    Args:
        correlation_id: The correlation ID to use
    """
  LogContext.set_correlation_id(correlation_id)

def add_log_context(key: str, value: Any) -> None:
  """
    Add a key-value pair to the logging context.
    
    Args:
        key: Context key
        value: Context value
    """
  LogContext.add_context(key, value)

def clear_log_context() -> None:
  """Clear all logging context data except correlation ID."""
  LogContext.clear_context()

# Add trace function to the standard logging module for type checking compatibility
def trace(self, message, *args, **kws):
  """Log a message with TRACE level."""
  if self.isEnabledFor(TRACE_LEVEL):
    self._log(TRACE_LEVEL, message, args, **kws)

# Add the trace method to the Logger class
logging.Logger.trace = trace # type: ignore
