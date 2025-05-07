#!/usr/bin/env python3
"""
Apply a specified YAPF style configuration inline to all Python files in sibling directories.

This script locates all sibling directories under the project root and reformats every `.py` file using an inline style dict.
"""

from pathlib import Path
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

def main(base_dir: Path):
  # Iterate over all sibling directories (excluding this script's own directory)
  for sibling in base_dir.iterdir():
    if sibling.is_dir():
      for py_file in sibling.rglob('*.py'):
        print(f"Formatting {py_file}")
        # In-place formatting with inline style dict
        FormatFile(
          filename=str(py_file),
          in_place=True,
          style_config=YAPF_STYLE
        )


if __name__ == '__main__':
  main(Path(__file__).parent)
