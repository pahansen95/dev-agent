"""
Filesystem operations utility module.

Provides a consistent interface for file operations throughout the KB Generator.
"""

import os
import re
from typing import List, Optional

# Import the protocol interface
from .._core.types.protocols import FileSystemService
from .logger import get_logger

# Get a logger for this module
logger = get_logger(__name__)
logger.debug("Initializing FileSystem utility")

class FileSystem(FileSystemService):
    """File system operations implementing the FileSystemService protocol."""

    @staticmethod
    def ensure_directory(directory: str) -> None:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory: The directory path to ensure exists
            
        Raises:
            IOError: If the directory can't be created
        """
        logger.debug(f"Ensuring directory exists: {directory}")
        try:
            os.makedirs(directory, exist_ok=True)
            logger.trace(f"Directory exists or was created: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {str(e)}", exc_info=True)
            raise IOError(f"Failed to create directory {directory}: {str(e)}")

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
        logger.debug(f"Reading file: {filepath} (encoding: {encoding})")
        try:
            with open(filepath, "r", encoding=encoding) as f:
                content = f.read()
                size = len(content)
                logger.trace(f"Read {size} bytes from {filepath}")
                return content
        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
            raise
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {str(e)}", exc_info=True)
            raise IOError(f"Error reading file {filepath}: {str(e)}")

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
        logger.debug(f"Writing file: {filepath} (encoding: {encoding}, size: {len(content)} bytes)")
        try:
            # Ensure the directory exists
            directory = os.path.dirname(os.path.abspath(filepath))
            os.makedirs(directory, exist_ok=True)
            logger.trace(f"Ensured directory exists: {directory}")

            with open(filepath, "w", encoding=encoding) as f:
                f.write(content)
                logger.trace(f"Successfully wrote {len(content)} bytes to {filepath}")
        except Exception as e:
            logger.error(f"Error writing to file {filepath}: {str(e)}", exc_info=True)
            raise IOError(f"Error writing to file {filepath}: {str(e)}")

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
        logger.debug(f"Listing files in directory: {directory}" + (f" with pattern: {pattern}" if pattern else ""))

        if not os.path.exists(directory):
            logger.error(f"Directory not found: {directory}")
            raise FileNotFoundError(f"Directory not found: {directory}")

        try:
            files = [os.path.join(directory, f) for f in os.listdir(directory) 
                   if os.path.isfile(os.path.join(directory, f))]

            if pattern:
                logger.trace(f"Filtering files with pattern: {pattern}")
                regex = re.compile(pattern)
                files = [f for f in files if regex.search(os.path.basename(f))]

            logger.debug(f"Found {len(files)} files" + 
                       (f" matching pattern '{pattern}'" if pattern else ""))
            logger.trace(f"Files: {', '.join(os.path.basename(f) for f in files[:5])}" + 
                       (f" and {len(files)-5} more" if len(files) > 5 else ""))
            return files

        except Exception as e:
            logger.error(f"Error listing files in directory {directory}: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def file_exists(filepath: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            filepath: Path to the file to check
            
        Returns:
            True if the file exists, False otherwise
        """
        logger.trace(f"Checking if file exists: {filepath}")
        exists = os.path.isfile(filepath)
        logger.trace(f"File {filepath} {'exists' if exists else 'does not exist'}")
        return exists

logger.debug("FileSystem utility initialized")