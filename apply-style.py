#!/usr/bin/env python3
"""
Apply a specified YAPF style configuration inline to all Python files in sibling directories.

This script locates all sibling directories under the project root and reformats every `.py` file using an inline style dict.
"""

import sys
from pathlib import Path
from typing import Generator, List
from yapf.yapflib.yapf_api import FormatFile

# Inline YAPF style configuration
YAPF_STYLE = {
  # Base style
  'based_on_style': 'pep8',

  # Indentation
  'indent_width': 2,
  'continuation_align_style': 'SPACE',
  'continuation_indent_width': 2,

  # Line length (assumed around 100; adjust as needed)
  'column_limit': 160,

  # Blank lines
  'blank_lines_around_top_level_definition': 1,
  'blank_line_before_module_docstring': False,
  'blank_line_before_class_docstring': True,
  'blank_line_before_nested_class_or_def': True,

  # Comment spacing
  'spaces_before_comment': 1,

  # Bracket & delimiter rules
  'space_inside_brackets': False,
  'spaces_around_dict_delimiters': False,
  'dedent_closing_brackets': False,
  'coalesce_brackets': False,

  # Splitting preferences
  'split_before_logical_operator': True,
  'split_before_first_argument': True,
}

PROJ_ROOT = Path(__file__).parent

def apply_style_to_file(file: Path) -> bool:
  """
  Apply YAPF styling to a single Python file.
  
  Args:
      file: Path to the Python file to format
      
  Returns:
      bool: True if formatting was successful, False otherwise
  """
  try:
    print(f"Formatting {file}")
    # In-place formatting with inline style dict
    reformatted, _, _ = FormatFile(filename=str(file), in_place=True, style_config=YAPF_STYLE)
    return reformatted
  except Exception as e:
    print(f"Error formatting {file}: {e}", file=sys.stderr)
    return False

def file_okay(file: Path) -> bool:
  return (file.is_file() and file.name.endswith('.py') and not file.name.startswith('.'))

def find_files(dir_tree: Path) -> Generator[Path, None, None]:
  """
  Find all Python files in the given directory tree.
  
  Args:
      dir_tree: Root directory to search for Python files
      
  Yields:
      Path objects for each Python file found
  """
  assert dir_tree.exists() and dir_tree.resolve().is_dir(), f"Directory {dir_tree} does not exist or is not a directory"

  for child in dir_tree.iterdir():
    r_child = child.resolve()
    if r_child.is_dir(): yield from find_files(child)
    elif file_okay(child):
      yield child

def main(*targets: str) -> List[str]:
  """
  Apply YAPF formatting to specified targets.
  
  Args:
      *targets: Paths to files or directories to format, relative to the project root
      
  Returns:
      List of paths that were skipped (not found or not accessible)
  """
  skipped = []

  for trgt in targets:
    print(f'Considering {trgt}')
    trgt_path = PROJ_ROOT / trgt
    if trgt_path.resolve().is_dir():
      for file in find_files(trgt_path):
        apply_style_to_file(file)
    else: # Maybe a file
      if file_okay(trgt_path): apply_style_to_file(trgt_path)
      else:
        print(f"Skipping {trgt_path} - not a Python file or directory")
        skipped.append(str(trgt_path))

  return skipped

if __name__ == '__main__':
  # If command line arguments are provided, use them instead of defaults
  if len(sys.argv) > 1:
    targets = sys.argv[1:]
  else:
    targets = ['src', 'tests', 'tools', Path(__file__).name]

  skipped = main(*targets)

  if skipped:
    print(f"\nSkipped {len(skipped)} targets:")
    for path in skipped:
      print(f"  - {path}")
