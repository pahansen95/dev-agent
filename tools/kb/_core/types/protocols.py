"""
Protocol interfaces for Knowledge Base Generator.

Defines protocol interfaces to formalize boundaries between components
and reduce coupling in the system.
"""

from typing import Protocol, Dict, List, Any, Optional


class FileSystemService(Protocol):
    """Protocol for filesystem operations."""

    def ensure_directory(self, directory: str) -> None:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory: The directory path to ensure exists
            
        Raises:
            IOError: If the directory can't be created
        """
        ...

    def read_file(self, filepath: str, encoding: str = "utf-8") -> str:
        """
        Read content from a file.
        
        Args:
            filepath: Path to the file to read
            encoding: Text encoding to use
            
        Returns:
            The file content as a string
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        ...

    def write_file(self, filepath: str, content: str, encoding: str = "utf-8") -> None:
        """
        Write content to a file.
        
        Args:
            filepath: Path to the file to write
            content: Content to write to the file
            encoding: Text encoding to use
            
        Raises:
            IOError: If there's an error writing to the file
        """
        ...

    def list_files(self, directory: str, pattern: Optional[str] = None) -> List[str]:
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
        ...

    def file_exists(self, filepath: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            filepath: Path to the file to check
            
        Returns:
            True if the file exists, False otherwise
        """
        ...


class LLMService(Protocol):
    """Protocol for language model service interactions."""

    def complete(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        max_tokens: int = 2000, 
        temperature: float = 0.7
    ) -> str:
        """
        Generate a completion from the language model.
        
        Args:
            system_prompt: The system instructions to guide the model behavior
            user_prompt: The specific user query or content to process
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0-1.0)
        
        Returns:
            The generated completion text
            
        Raises:
            RuntimeError: If the API request fails after retries
        """
        ...