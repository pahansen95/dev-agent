"""
Filesystem operations utility module.

Provides a consistent interface for file operations throughout the KB Generator.
"""

import os
import re
from typing import List, Optional

class FileSystem:

  """File system operations."""

  @staticmethod
  def ensure_directory(directory: str) -> None:
    """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory: The directory path to ensure exists
            
        Raises:
            IOError: If the directory can't be created
        """
    os.makedirs(directory, exist_ok=True)

  @staticmethod
  def read_file(filepath: str, encoding: str = "utf-8") -> str:
    """
        Read content from a file.
        
        Args:
            filepath: Path to the file to read
            encoding: Text encoding to use (default: utf-8)
            
        Returns:
            The file content as a string
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
    with open(filepath, "r", encoding=encoding) as f:
      return f.read()

  @staticmethod
  def write_file(filepath: str, content: str, encoding: str = "utf-8") -> None:
    """
        Write content to a file.
        
        Args:
            filepath: Path to the file to write
            content: Content to write to the file
            encoding: Text encoding to use (default: utf-8)
            
        Raises:
            IOError: If there's an error writing to the file
        """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    with open(filepath, "w", encoding=encoding) as f:
      f.write(content)

  @staticmethod
  def list_files(directory: str, pattern: Optional[str] = None) -> List[str]:
    """
        List files in a directory, optionally filtered by a pattern.
        
        Args:
            directory: The directory path to list files from
            pattern: Optional regex pattern to filter files
            
        Returns:
            List of file paths matching the pattern
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
        """
    if not os.path.exists(directory):
      raise FileNotFoundError(f"Directory not found: {directory}")

    files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    if pattern:
      regex = re.compile(pattern)
      files = [f for f in files if regex.search(os.path.basename(f))]

    return files

  @staticmethod
  def file_exists(filepath: str) -> bool:
    """
        Check if a file exists.
        
        Args:
            filepath: Path to the file to check
            
        Returns:
            True if the file exists, False otherwise
        """
    return os.path.isfile(filepath)
