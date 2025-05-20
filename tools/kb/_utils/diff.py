"""
Diff management utility module.

Provides functionality for creating and applying diffs between text content.
"""

import difflib
import re

import logging

# Get a logger for this module
logger = logging.getLogger(__name__)
logger.debug("Initializing DiffManager utility")

class DiffManager:

  """Manages creation and application of diffs between text content."""

  @staticmethod
  def create_diff(original: str, modified: str) -> str:
    """
        Create a unified diff between two text strings.
        
        Args:
            original: The original text content
            modified: The modified text content
            
        Returns:
            A unified diff as a string
        """
    logger.debug("Creating unified diff between content versions")
    logger.trace(f"Original content size: {len(original)} bytes")
    logger.trace(f"Modified content size: {len(modified)} bytes")

    try:
      diff_lines = list(difflib.unified_diff(original.splitlines(), modified.splitlines(), fromfile="original", tofile="modified", lineterm=""))

      diff_content = "\n".join(diff_lines)
      logger.debug(f"Diff created with {len(diff_lines)} lines")

      # Log a summary of changes
      additions = len([line for line in diff_lines if line.startswith('+')])
      deletions = len([line for line in diff_lines if line.startswith('-')])
      logger.debug(f"Diff summary: {additions} additions, {deletions} deletions")

      return diff_content

    except Exception as e:
      logger.error(f"Error creating diff: {str(e)}", exc_info=True)
      raise

  @staticmethod
  def apply_diff(content: str, diff_content: str) -> str:
    """
        Apply a unified diff to a text string.
        
        Args:
            content: The original content to modify
            diff_content: The unified diff to apply
            
        Returns:
            The modified content with diff applied
            
        Raises:
            ValueError: If the diff cannot be applied cleanly
        """
    logger.debug("Applying diff to content")
    logger.trace(f"Original content size: {len(content)} bytes")
    logger.trace(f"Diff content size: {len(diff_content)} bytes")

    # Split content into lines
    lines = content.splitlines()
    result_lines = lines.copy()

    logger.trace(f"Content split into {len(lines)} lines")

    # Parse diff content into lines
    diff_lines = diff_content.splitlines()

    if not diff_lines:
      logger.debug("Empty diff - no changes to apply")
      return content # No changes

    # Track line offset to handle multiple diff hunks
    line_offset = 0
    current_line = None
    hunks_processed = 0

    # Process each line in the diff
    i = 0
    try:
      while i < len(diff_lines):
        line = diff_lines[i]

        # Handle diff headers to get line numbers
        if line.startswith("@@"):
          # Parse the @@ -a,b +c,d @@ format
          header_match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
          if not header_match:
            error_msg = f"Invalid diff header format: {line}"
            logger.error(error_msg)
            raise ValueError(error_msg)

          # Extract line numbers (1-based in diff, convert to 0-based)
          src_line = int(header_match.group(1)) - 1
          tgt_line = int(header_match.group(2)) - 1

          # Adjust for previous changes
          current_line = tgt_line + line_offset
          logger.trace(f"Processing hunk at line {current_line} (original line {tgt_line})")
          hunks_processed += 1

        # Process content lines
        elif line.startswith("-"):
          # Line should be removed
          if current_line is None:
            error_msg = "Malformed diff: content line before header"
            logger.error(error_msg)
            raise ValueError(error_msg)

          if 0 <= current_line < len(result_lines):
            logger.trace(f"Removing line at position {current_line}: '{result_lines[current_line][:50]}...'")
            result_lines.pop(current_line)
            line_offset -= 1
          else:
            error_msg = f"Diff error: trying to remove line {current_line} but content only has {len(result_lines)} lines"
            logger.error(error_msg)
            raise ValueError(error_msg)

        elif line.startswith("+"):
          # Line should be added
          if current_line is None:
            error_msg = "Malformed diff: content line before header"
            logger.error(error_msg)
            raise ValueError(error_msg)

          content_to_add = line[1:] # Remove the + prefix
          if 0 <= current_line <= len(result_lines):
            logger.trace(f"Adding line at position {current_line}: '{content_to_add[:50]}...'")
            result_lines.insert(current_line, content_to_add)
            current_line += 1
            line_offset += 1
          else:
            error_msg = f"Diff error: trying to add at line {current_line} but content only has {len(result_lines)} lines"
            logger.error(error_msg)
            raise ValueError(error_msg)

        elif not line.startswith("---") and not line.startswith("+++"):
          # Context line - just advance the position
          if current_line is not None:
            logger.trace(f"Context line at position {current_line}")
            current_line += 1

        i += 1

      # Reassemble the content
      result_content = "\n".join(result_lines)
      logger.debug(f"Diff applied successfully: processed {hunks_processed} hunks, resulting content size: {len(result_content)} bytes")
      return result_content

    except ValueError:
      # Re-raise ValueError exceptions which contain user-friendly messages
      raise
    except Exception as e:
      error_msg = f"Error applying diff: {str(e)}"
      logger.error(error_msg, exc_info=True)
      raise ValueError(error_msg)

logger.debug("DiffManager utility initialized")
