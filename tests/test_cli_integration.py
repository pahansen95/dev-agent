"""
Integration tests for the DevAgent CLI.

These tests verify the command-line interface functionality
by mocking the underlying APIs and simulating CLI interactions.
"""

import unittest
import sys
import os
import io
import tempfile
import shutil
import json
import pathlib
from unittest.mock import patch, MagicMock

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from DevAgent.interpreter.application.facade import InterpreterFacade

class TestCLIIntegration(unittest.TestCase):

  """Integration tests for the DevAgent CLI."""

  def setUp(self):
    """Set up test fixtures."""
    # Create a temporary directory for the test environment
    self.test_dir = tempfile.mkdtemp()
    self.devagent_dir = os.path.join(self.test_dir, '.devagent')
    os.makedirs(self.devagent_dir, exist_ok=True)

  def tearDown(self):
    """Clean up test fixtures."""
    # Remove the temporary directory
    shutil.rmtree(self.test_dir)

  @patch('DevAgent.__main__.OntologyAPI')
  def test_ontology_init_info(self, mock_ontology_api):
    """Test ontology init and info CLI commands."""
    from DevAgent.__main__ import handle_ontology_init, handle_ontology_info

    # Create mock graph
    mock_graph = {"nodes": {}, "edges": {}}
    mock_ontology_api.init.return_value = mock_graph
    mock_ontology_api.dump.return_value = mock_graph
    mock_ontology_api.load.return_value = mock_graph
    mock_ontology_api.info.return_value = (0, 0) # no nodes, no edges

    # Create a temporary file for the graph
    graph_file = os.path.join(self.test_dir, 'graph.json')

    # Prepare arguments for init
    init_args = MagicMock()
    init_args.output = graph_file

    # Redirect stdout to capture output
    original_stdout = sys.stdout
    stdout_capture = io.StringIO()
    sys.stdout = stdout_capture

    try:
      # Call init handler
      result = handle_ontology_init(init_args)

      # Verify result
      self.assertTrue(result)
      mock_ontology_api.init.assert_called_once()
      mock_ontology_api.dump.assert_called_once_with(mock_graph)

      # Check that the file exists
      self.assertTrue(os.path.exists(graph_file))

      # Reset stdout
      stdout_capture = io.StringIO()
      sys.stdout = stdout_capture

      # Prepare arguments for info
      info_args = MagicMock()
      info_args.input = graph_file

      # Call info handler
      result = handle_ontology_info(info_args)

      # Verify result
      self.assertTrue(result)
      mock_ontology_api.load.assert_called()
      mock_ontology_api.info.assert_called_with(mock_graph)

      # Check output
      output = stdout_capture.getvalue()
      self.assertIn("nodes=0", output)
      self.assertIn("edges=0", output)
    finally:
      sys.stdout = original_stdout

  @patch('DevAgent.__main__.OntologyAPI')
  def test_ontology_add_node_edge(self, mock_ontology_api):
    """Test adding nodes and edges to an ontology graph via CLI."""
    from DevAgent.__main__ import handle_ontology_init, handle_ontology_add_node, handle_ontology_add_edge, handle_ontology_info

    # Create mock graph objects for different stages
    mock_empty_graph = {"nodes": {}, "edges": {}}
    mock_one_node_graph = {"nodes": {"node1": {}}, "edges": {}}
    mock_two_nodes_graph = {"nodes": {"node1": {}, "node2": {}}, "edges": {}}
    mock_final_graph = {"nodes": {"node1": {}, "node2": {}}, "edges": {"edge1": {}}}

    # Set up mock API responses
    mock_ontology_api.init.return_value = mock_empty_graph
    mock_ontology_api.load.side_effect = [
      mock_empty_graph, # For first add-node
      mock_one_node_graph, # For second add-node
      mock_two_nodes_graph, # For add-edge
      mock_final_graph # For final info
    ]
    mock_ontology_api.dump.side_effect = [
      mock_empty_graph, # For init
      mock_one_node_graph, # For first add-node
      mock_two_nodes_graph, # For second add-node
      mock_final_graph # For add-edge
    ]
    mock_ontology_api.info.return_value = (2, 1) # 2 nodes, 1 edge

    # Create a temporary file for the graph
    graph_file = os.path.join(self.test_dir, 'graph.json')

    # Redirect stdout
    original_stdout = sys.stdout
    stdout_capture = io.StringIO()
    sys.stdout = stdout_capture

    try:
      # Initialize graph
      init_args = MagicMock()
      init_args.output = graph_file
      handle_ontology_init(init_args)

      # Add first node
      node1_args = MagicMock()
      node1_args.input = graph_file
      node1_args.output = graph_file
      node1_args.id = "node1"
      node1_args.label = "Node 1"
      node1_args.kind = "concept"
      node1_args.meta = "{}"

      result = handle_ontology_add_node(node1_args)
      self.assertTrue(result)
      mock_ontology_api.add_node.assert_called_with(mock_empty_graph, "node1", "Node 1", "concept", {})

      # Add second node
      node2_args = MagicMock()
      node2_args.input = graph_file
      node2_args.output = graph_file
      node2_args.id = "node2"
      node2_args.label = "Node 2"
      node2_args.kind = "concept"
      node2_args.meta = "{}"

      result = handle_ontology_add_node(node2_args)
      self.assertTrue(result)
      mock_ontology_api.add_node.assert_called_with(mock_one_node_graph, "node2", "Node 2", "concept", {})

      # Add edge
      edge_args = MagicMock()
      edge_args.input = graph_file
      edge_args.output = graph_file
      edge_args.src = "node1"
      edge_args.rel = "RELATED_TO"
      edge_args.dst = "node2"

      result = handle_ontology_add_edge(edge_args)
      self.assertTrue(result)
      mock_ontology_api.add_edge.assert_called_with(mock_two_nodes_graph, "node1", "RELATED_TO", "node2")

      # Check info
      stdout_capture = io.StringIO()
      sys.stdout = stdout_capture

      info_args = MagicMock()
      info_args.input = graph_file
      result = handle_ontology_info(info_args)
      self.assertTrue(result)

      output = stdout_capture.getvalue()
      self.assertIn("nodes=2", output)
      self.assertIn("edges=1", output)
    finally:
      sys.stdout = original_stdout

  def test_interpreter_session_lifecycle(self):
    """Test the lifecycle of an interpreter session via CLI."""
    from DevAgent.__main__ import handle_interpreter_session_create, handle_interpreter_session_list, handle_interpreter_session_delete

    # Set up mock interpreter facade directly at the module level where it's imported
    mock_interpreter = MagicMock(spec=InterpreterFacade)
    with patch('DevAgent.__main__.create_interpreter', return_value=mock_interpreter) as mock_create_interpreter:

      # Set up mock responses
      mock_interpreter.create_session.return_value = {"success": True, "session_id": "sid-12345678", "error": None}
      mock_interpreter.list_sessions.side_effect = [
          {  # First call - after creation
              "success": True,
              "sessions": [
                  {
                      "id": "sid-12345678",
                      "name": "test_session",
                      "kernel_count": 0,
                      "path": f"{self.devagent_dir}/by-id/sessions/sid-12345678"
                  }
              ],
              "error": None
          },
          {  # Second call - after deletion
              "success": True,
              "sessions": [],
              "error": None
          }
      ]
      mock_interpreter.delete_session.return_value = {"success": True, "error": None}

      # Redirect stdout
      original_stdout = sys.stdout
      stdout_capture = io.StringIO()
      sys.stdout = stdout_capture

      try:
        # Create session
        create_args = MagicMock()
        create_args.dir = self.devagent_dir
        create_args.name = "test_session"

        result = handle_interpreter_session_create(create_args)
        self.assertTrue(result)
        mock_create_interpreter.assert_called_with(pathlib.Path(self.devagent_dir))
        mock_interpreter.create_session.assert_called_with("test_session")

        create_output = stdout_capture.getvalue()
        self.assertIn("Session created: test_session", create_output)

        # List sessions
        stdout_capture = io.StringIO()
        sys.stdout = stdout_capture

        list_args = MagicMock()
        list_args.dir = self.devagent_dir

        result = handle_interpreter_session_list(list_args)
        self.assertTrue(result)

        list_output = stdout_capture.getvalue()
        self.assertIn("Active sessions:", list_output)
        self.assertIn("Name: test_session", list_output)

        # Delete session
        stdout_capture = io.StringIO()
        sys.stdout = stdout_capture

        delete_args = MagicMock()
        delete_args.dir = self.devagent_dir
        delete_args.session = "test_session"

        result = handle_interpreter_session_delete(delete_args)
        self.assertTrue(result)
        mock_interpreter.delete_session.assert_called_with("test_session")

        delete_output = stdout_capture.getvalue()
        self.assertIn("deleted successfully", delete_output)

        # List sessions again (should be empty)
        stdout_capture = io.StringIO()
        sys.stdout = stdout_capture

        result = handle_interpreter_session_list(list_args)
        self.assertTrue(result)

        list_output = stdout_capture.getvalue()
        self.assertIn("No active sessions", list_output)

      finally:
        sys.stdout = original_stdout

  def test_help_commands(self):
    """Test that help commands produce the expected output."""
    # Create mock parser and subparsers
    with patch('DevAgent.__main__.setup_argument_parser') as mock_setup_parser, \
        patch('DevAgent.__main__.logging'):

      mock_parser = MagicMock()
      mock_ontology_parser = MagicMock()
      mock_interpreter_parser = MagicMock()
      mock_session_parser = MagicMock()
      mock_kernel_parser = MagicMock()

      mock_setup_parser.return_value = mock_parser

      # Configure the mock parser to simulate argparse behavior
      def mock_parse_args():
        # Simulate parsing '--help'
        parser = mock_setup_parser()
        parser.print_help()
        sys.exit(0)

      mock_parser.parse_args.side_effect = mock_parse_args

      # Set up parser action hierarchy
      mock_parser._actions = [MagicMock(), MagicMock()] # Create two elements in the list
      mock_parser._actions[1].choices = {"ontology": mock_ontology_parser, "interpreter": mock_interpreter_parser}

      mock_interpreter_parser._actions = [MagicMock()]
      mock_interpreter_parser._actions[0].choices = {"session": mock_session_parser, "kernel": mock_kernel_parser}

      # Set up help text
      mock_parser.format_help.return_value = "DevAgent: Agentic Development Tool"
      mock_ontology_parser.format_help.return_value = "Ontology graph operations"
      mock_interpreter_parser.format_help.return_value = "Interpreter operations"
      mock_session_parser.format_help.return_value = "Session management operations"
      mock_kernel_parser.format_help.return_value = "Kernel management operations"

      # Test main help
      from DevAgent.__main__ import main

      # Redirect stdout to capture output
      original_stdout = sys.stdout
      stdout_capture = io.StringIO()
      sys.stdout = stdout_capture

      try:
        with patch('sys.argv', ['devagent', '--help']), \
            patch('sys.exit') as mock_exit:

          mock_exit.side_effect = SystemExit(0)
          try:
            main()
          except SystemExit:
            pass

          mock_parser.print_help.assert_called_once()
      finally:
        sys.stdout = original_stdout

if __name__ == "__main__":
  unittest.main()
