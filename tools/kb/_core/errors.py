"""
Error definitions for the Knowledge Base Generator.

This module defines all exceptions used throughout the KB Generator tool.
"""

class KBError(Exception):

  """Base exception class for all KB Generator errors."""
  pass

class ConfigurationError(KBError):

  """Exception raised for errors in the application configuration."""
  pass

class TemplateError(KBError):

  """Exception raised for errors with prompt templates."""
  pass

class GuidanceError(KBError):

  """Exception raised for errors with guidance parameters."""
  pass

class ContentGenerationError(KBError):

  """Exception raised for errors during content generation."""
  pass

class ParsingError(KBError):

  """Exception raised for errors during markdown parsing."""
  pass
