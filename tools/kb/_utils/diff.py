"""
Diff management utility module.

Provides functionality for creating and applying diffs between text content.
"""

import difflib
import re

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
    diff_lines = list(difflib.unified_diff(original.splitlines(), modified.splitlines(), fromfile="original", tofile="modified", lineterm=""))
    return "\n".join(diff_lines)

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
    # Split content into lines
    lines = content.splitlines()
    result_lines = lines.copy()

    # Parse diff content into lines
    diff_lines = diff_content.splitlines()

    if not diff_lines:
      return content # No changes

    # Track line offset to handle multiple diff hunks
    line_offset = 0
    current_line = None

    # Process each line in the diff
    i = 0
    while i < len(diff_lines):
      line = diff_lines[i]

      # Handle diff headers to get line numbers
      if line.startswith("@@"):
        # Parse the @@ -a,b +c,d @@ format
        header_match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if not header_match:
          raise ValueError(f"Invalid diff header format: {line}")

        # Extract line numbers (1-based in diff, convert to 0-based)
        src_line = int(header_match.group(1)) - 1
        tgt_line = int(header_match.group(2)) - 1

        # Adjust for previous changes
        current_line = tgt_line + line_offset

      # Process content lines
      elif line.startswith("-"):
        # Line should be removed
        if current_line is None:
          raise ValueError("Malformed diff: content line before header")

        if 0 <= current_line < len(result_lines):
          result_lines.pop(current_line)
          line_offset -= 1
        else:
          raise ValueError(f"Diff error: trying to remove line {current_line} but "
                           f"content only has {len(result_lines)} lines")

      elif line.startswith("+"):
        # Line should be added
        if current_line is None:
          raise ValueError("Malformed diff: content line before header")

        content_to_add = line[1:] # Remove the + prefix
        if 0 <= current_line <= len(result_lines):
          result_lines.insert(current_line, content_to_add)
          current_line += 1
          line_offset += 1
        else:
          raise ValueError(f"Diff error: trying to add at line {current_line} but "
                           f"content only has {len(result_lines)} lines")

      elif not line.startswith("---") and not line.startswith("+++"):
        # Context line - just advance the position
        if current_line is not None:
          current_line += 1

      i += 1

    # Reassemble the content
    return "\n".join(result_lines)
