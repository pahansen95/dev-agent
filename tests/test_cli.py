"""
Test suite for the DevAgent CLI.

This test suite verifies the command-line interface functionality
by mocking the underlying APIs and verifying command parsing works correctly.
"""

import unittest
import sys
import io
import tempfile
import os
import json
import pathlib
from unittest.mock import patch, MagicMock

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the main module so we can test it
from DevAgent.__main__ import (
    setup_argument_parser, 
    handle_ontology_init,
    handle_ontology_info,
    handle_ontology_dump,
    handle_ontology_add_node,
    handle_ontology_add_edge,
    handle_interpreter_session_create,
    handle_interpreter_session_list,
    handle_interpreter_session_delete,
    handle_interpreter_session_execute,
    handle_interpreter_kernel_create,
    handle_interpreter_kernel_list,
    handle_interpreter_kernel_execute,
    handle_interpreter_kernel_restart,
    handle_interpreter_kernel_interrupt,
    handle_interpreter_kernel_delete,
    main
)

class TestCLIArgumentParser(unittest.TestCase):
    """Tests for the command-line argument parser."""
    
    def test_setup_argument_parser(self):
        """Test that the argument parser is set up correctly."""
        parser = setup_argument_parser()
        
        # Test that basic structure is correct
        self.assertEqual(parser.description, "DevAgent: Agentic Development Tool")
        
        # Test that log level argument exists
        self.assertTrue(any(action.dest == "log_level" for action in parser._actions))
        
        # Test that subcommands exist
        subcommands = [action for action in parser._actions if action.dest == "command"]
        self.assertEqual(len(subcommands), 1)
        
        # Test that ontology and interpreter subcommands exist
        choices = getattr(subcommands[0], "choices", {})
        self.assertIn("ontology", choices)
        self.assertIn("interpreter", choices)
    
    def test_parser_defaults(self):
        """Test that the argument parser has correct defaults."""
        parser = setup_argument_parser()
        
        # Check log level default
        for action in parser._actions:
            if action.dest == "log_level":
                self.assertEqual(action.default, "INFO")
        
        # Check interpreter dir default
        for action in parser._subparsers._group_actions:
            if action.dest == "command" and "interpreter" in action.choices:
                for subaction in action.choices["interpreter"]._actions:
                    if subaction.dest == "dir":
                        self.assertTrue(subaction.default.endswith('.devagent'))
    
    def test_parser_subcommands(self):
        """Test that subcommands have correct structure."""
        parser = setup_argument_parser()
        
        # Get main subparsers
        main_subparsers = None
        for action in parser._actions:
            if action.dest == "command":
                main_subparsers = action
                break
        
        # Check ontology subcommands
        ontology_parser = main_subparsers.choices["ontology"]
        ontology_subparsers = None
        for action in ontology_parser._actions:
            if action.dest == "subcommand":
                ontology_subparsers = action
                break
        
        self.assertIsNotNone(ontology_subparsers)
        self.assertIn("init", ontology_subparsers.choices)
        self.assertIn("info", ontology_subparsers.choices)
        self.assertIn("dump", ontology_subparsers.choices)
        self.assertIn("add-node", ontology_subparsers.choices)
        self.assertIn("add-edge", ontology_subparsers.choices)
        
        # Check interpreter subcommands
        interpreter_parser = main_subparsers.choices["interpreter"]
        interpreter_subparsers = None
        for action in interpreter_parser._actions:
            if action.dest == "subcommand":
                interpreter_subparsers = action
                break
        
        self.assertIsNotNone(interpreter_subparsers)
        self.assertIn("session", interpreter_subparsers.choices)
        self.assertIn("kernel", interpreter_subparsers.choices)


class TestOntologyCommands(unittest.TestCase):
    """Tests for the ontology commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.original_stdout = sys.stdout
        self.stdout = io.StringIO()
        sys.stdout = self.stdout
    
    def tearDown(self):
        """Clean up test fixtures."""
        sys.stdout = self.original_stdout
    
    @patch('DevAgent.__main__.OntologyAPI')
    def test_handle_ontology_init(self, mock_ontology_api):
        """Test handling the ontology init command."""
        # Set up mock
        mock_graph = {"nodes": {}, "edges": {}}
        mock_ontology_api.init.return_value = mock_graph
        mock_ontology_api.dump.return_value = mock_graph
        
        # Set up args
        args = MagicMock()
        args.output = "-"  # Write to stdout
        
        # Run command
        result = handle_ontology_init(args)
        
        # Verify results
        self.assertTrue(result)
        mock_ontology_api.init.assert_called_once()
        mock_ontology_api.dump.assert_called_once_with(mock_graph)
        
        # Check stdout
        output = self.stdout.getvalue()
        expected_output = json.dumps(mock_graph, indent=2) + "\n"
        self.assertEqual(output, expected_output)
    
    @patch('DevAgent.__main__.OntologyAPI')
    def test_handle_ontology_info(self, mock_ontology_api):
        """Test handling the ontology info command."""
        # Set up mock
        mock_graph = {"nodes": {}, "edges": {}}
        mock_ontology_api.load.return_value = mock_graph
        mock_ontology_api.info.return_value = (0, 0)  # no nodes, no edges
        
        # Create temporary file with a graph
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            json.dump(mock_graph, temp_file)
            temp_file_path = temp_file.name
        
        try:
            # Set up args
            args = MagicMock()
            args.input = temp_file_path
            
            # Run command
            result = handle_ontology_info(args)
            
            # Verify results
            self.assertTrue(result)
            mock_ontology_api.load.assert_called_once()
            mock_ontology_api.info.assert_called_once_with(mock_graph)
            
            # Check stdout
            output = self.stdout.getvalue()
            self.assertIn("nodes=0", output)
            self.assertIn("edges=0", output)
        finally:
            # Clean up
            os.unlink(temp_file_path)
    
    @patch('DevAgent.__main__.OntologyAPI')
    def test_handle_ontology_dump(self, mock_ontology_api):
        """Test handling the ontology dump command."""
        # Set up mock
        mock_graph = {"nodes": {}, "edges": {}}
        mock_ontology_api.load.return_value = mock_graph
        mock_ontology_api.dump.return_value = mock_graph
        
        # Create temporary file with a graph
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            json.dump(mock_graph, temp_file)
            temp_file_path = temp_file.name
        
        try:
            # Set up args
            args = MagicMock()
            args.input = temp_file_path
            args.output = "-"  # Write to stdout
            
            # Run command
            result = handle_ontology_dump(args)
            
            # Verify results
            self.assertTrue(result)
            mock_ontology_api.load.assert_called_once()
            mock_ontology_api.dump.assert_called_once_with(mock_graph)
            
            # Check stdout
            output = self.stdout.getvalue()
            expected_output = json.dumps(mock_graph, indent=2) + "\n"
            self.assertEqual(output, expected_output)
        finally:
            # Clean up
            os.unlink(temp_file_path)
    
    @patch('DevAgent.__main__.OntologyAPI')
    def test_handle_ontology_add_node(self, mock_ontology_api):
        """Test handling the ontology add-node command."""
        # Set up mock
        mock_graph = {"nodes": {}, "edges": {}}
        mock_ontology_api.load.return_value = mock_graph
        mock_ontology_api.dump.return_value = {"nodes": {"node1": {}}, "edges": {}}
        
        # Create temporary file with a graph
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            json.dump(mock_graph, temp_file)
            temp_file_path = temp_file.name
        
        try:
            # Set up args
            args = MagicMock()
            args.input = temp_file_path
            args.output = "-"  # Write to stdout
            args.id = "node1"
            args.label = "Node 1"
            args.kind = "concept"
            args.meta = "{}"
            
            # Run command
            result = handle_ontology_add_node(args)
            
            # Verify results
            self.assertTrue(result)
            mock_ontology_api.load.assert_called_once()
            mock_ontology_api.add_node.assert_called_once_with(mock_graph, "node1", "Node 1", "concept", {})
            mock_ontology_api.dump.assert_called_once_with(mock_graph)
            
            # Check stdout
            output = self.stdout.getvalue()
            expected_output = json.dumps({"nodes": {"node1": {}}, "edges": {}}, indent=2) + "\n"
            self.assertEqual(output, expected_output)
        finally:
            # Clean up
            os.unlink(temp_file_path)
    
    @patch('DevAgent.__main__.OntologyAPI')
    def test_handle_ontology_add_edge(self, mock_ontology_api):
        """Test handling the ontology add-edge command."""
        # Set up mock
        mock_graph = {"nodes": {"node1": {}, "node2": {}}, "edges": {}}
        mock_ontology_api.load.return_value = mock_graph
        mock_ontology_api.dump.return_value = {"nodes": {"node1": {}, "node2": {}}, "edges": {"edge1": {}}}
        
        # Create temporary file with a graph
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            json.dump(mock_graph, temp_file)
            temp_file_path = temp_file.name
        
        try:
            # Set up args
            args = MagicMock()
            args.input = temp_file_path
            args.output = "-"  # Write to stdout
            args.src = "node1"
            args.rel = "RELATED_TO"
            args.dst = "node2"
            
            # Run command
            result = handle_ontology_add_edge(args)
            
            # Verify results
            self.assertTrue(result)
            mock_ontology_api.load.assert_called_once()
            mock_ontology_api.add_edge.assert_called_once_with(mock_graph, "node1", "RELATED_TO", "node2")
            mock_ontology_api.dump.assert_called_once_with(mock_graph)
            
            # Check stdout
            output = self.stdout.getvalue()
            expected_output = json.dumps({"nodes": {"node1": {}, "node2": {}}, "edges": {"edge1": {}}}, indent=2) + "\n"
            self.assertEqual(output, expected_output)
        finally:
            # Clean up
            os.unlink(temp_file_path)


class TestInterpreterSessionCommands(unittest.TestCase):
    """Tests for the interpreter session commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.original_stdout = sys.stdout
        self.stdout = io.StringIO()
        sys.stdout = self.stdout
        
        # Create a temporary directory for the tests
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        sys.stdout = self.original_stdout
        
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_session_create(self, mock_interpreter):
        """Test handling the interpreter session create command."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.create_session.return_value = {
            "success": True,
            "session_id": "sid-12345678",
            "error": None
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        args.name = "test_session"
        
        # Run command
        result = handle_interpreter_session_create(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.create_session.assert_called_once_with("test_session")
        
        # Check output
        output = self.stdout.getvalue()
        self.assertIn("Session created: test_session", output)
        self.assertIn("Session ID: sid-12345678", output)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_session_create_failure(self, mock_interpreter):
        """Test handling the interpreter session create command with failure."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.create_session.return_value = {
            "success": False,
            "session_id": None,
            "error": "Session already exists"
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        args.name = "test_session"
        
        # Run command
        result = handle_interpreter_session_create(args)
        
        # Verify results
        self.assertFalse(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.create_session.assert_called_once_with("test_session")
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_session_list(self, mock_interpreter):
        """Test handling the interpreter session list command."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.list_sessions.return_value = {
            "success": True,
            "sessions": [
                {
                    "id": "sid-12345678",
                    "name": "test_session",
                    "kernel_count": 0,
                    "path": f"{self.temp_dir}/by-id/sessions/sid-12345678"
                }
            ],
            "error": None
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        
        # Run command
        result = handle_interpreter_session_list(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.list_sessions.assert_called_once()
        
        # Check output
        output = self.stdout.getvalue()
        self.assertIn("Active sessions:", output)
        self.assertIn("Name: test_session", output)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_session_list_empty(self, mock_interpreter):
        """Test handling the interpreter session list command with no sessions."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.list_sessions.return_value = {
            "success": True,
            "sessions": [],
            "error": None
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        
        # Run command
        result = handle_interpreter_session_list(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.list_sessions.assert_called_once()
        
        # Check output
        output = self.stdout.getvalue()
        self.assertIn("No active sessions", output)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_session_delete(self, mock_interpreter):
        """Test handling the interpreter session delete command."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.delete_session.return_value = {
            "success": True,
            "error": None
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        args.session = "test_session"
        
        # Run command
        result = handle_interpreter_session_delete(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.delete_session.assert_called_once_with("test_session")
        
        # Check output
        output = self.stdout.getvalue()
        self.assertIn("deleted successfully", output)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_session_execute(self, mock_interpreter):
        """Test handling the interpreter session execute command."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.execute_code.return_value = {
            "success": True,
            "stdout": "Hello, World!",
            "error": None,
            "outputs": [],
            "execution_time": 0.1
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        args.session = "test_session"
        args.kernel = "test_kernel"
        args.code = "print('Hello, World!')"
        
        # Run command
        result = handle_interpreter_session_execute(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.execute_code.assert_called_once_with("test_session/test_kernel", "print('Hello, World!')")
        
        # Check output
        output = self.stdout.getvalue()
        self.assertEqual(output, "Hello, World!\n")


class TestInterpreterKernelCommands(unittest.TestCase):
    """Tests for the interpreter kernel commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.original_stdout = sys.stdout
        self.stdout = io.StringIO()
        sys.stdout = self.stdout
        
        # Create a temporary directory for the tests
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        sys.stdout = self.original_stdout
        
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_kernel_create(self, mock_interpreter):
        """Test handling the interpreter kernel create command."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.create_kernel.return_value = {
            "success": True,
            "kernel_id": "kid-12345678",
            "error": None
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        args.session = "test_session"
        args.name = "test_kernel"
        args.type = "python3"
        
        # Run command
        result = handle_interpreter_kernel_create(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.create_kernel.assert_called_once_with("test_session", "test_kernel", "python3")
        
        # Check output
        output = self.stdout.getvalue()
        self.assertIn("Kernel created: test_kernel", output)
        self.assertIn("Kernel ID: kid-12345678", output)
        self.assertIn("Kernel Type: python3", output)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_kernel_list(self, mock_interpreter):
        """Test handling the interpreter kernel list command."""
        # Set up mock for the list_kernels method
        mock_instance = mock_interpreter.return_value
        mock_instance.list_kernels.return_value = {
            "success": True,
            "kernels": [
                {
                    "id": "kid-12345678",
                    "name": "test_kernel",
                    "kernel_type": "python3",
                    "is_alive": True
                }
            ],
            "error": None
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        args.session = "test_session"
        
        # Run command
        result = handle_interpreter_kernel_list(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.list_kernels.assert_called_once_with("test_session")
        
        # Check output
        output = self.stdout.getvalue()
        self.assertIn("Kernels in session 'test_session'", output)
        self.assertIn("test_kernel", output)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_kernel_execute(self, mock_interpreter):
        """Test handling the interpreter kernel execute command."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.execute_code.return_value = {
            "success": True,
            "stdout": "Hello, World!",
            "error": None,
            "outputs": [],
            "execution_time": 0.1
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        args.ref = "test_session/test_kernel"
        args.code = "print('Hello, World!')"
        args.file = None
        
        # Run command
        result = handle_interpreter_kernel_execute(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.execute_code.assert_called_once_with("test_session/test_kernel", "print('Hello, World!')")
        
        # Check output
        output = self.stdout.getvalue()
        self.assertEqual(output, "Hello, World!\n")
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_kernel_execute_from_file(self, mock_interpreter):
        """Test handling the interpreter kernel execute command with code from file."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.execute_code.return_value = {
            "success": True,
            "stdout": "Hello, World!",
            "error": None,
            "outputs": [],
            "execution_time": 0.1
        }
        
        # Create a temporary file with code
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("print('Hello, World!')")
            temp_file_path = temp_file.name
        
        try:
            # Set up args
            args = MagicMock()
            args.dir = self.temp_dir
            args.ref = "test_session/test_kernel"
            args.code = None
            args.file = temp_file_path
            
            # Run command
            result = handle_interpreter_kernel_execute(args)
            
            # Verify results
            self.assertTrue(result)
            mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
            mock_instance.execute_code.assert_called_once_with("test_session/test_kernel", "print('Hello, World!')")
            
            # Check output
            output = self.stdout.getvalue()
            self.assertEqual(output, "Hello, World!\n")
        finally:
            # Clean up
            os.unlink(temp_file_path)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_kernel_restart(self, mock_interpreter):
        """Test handling the interpreter kernel restart command."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.restart_kernel.return_value = {
            "success": True,
            "error": None
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        args.ref = "test_session/test_kernel"
        
        # Run command
        result = handle_interpreter_kernel_restart(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.restart_kernel.assert_called_once_with("test_session/test_kernel")
        
        # Check output
        output = self.stdout.getvalue()
        self.assertIn("restarted successfully", output)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_kernel_interrupt(self, mock_interpreter):
        """Test handling the interpreter kernel interrupt command."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.interrupt_kernel.return_value = {
            "success": True,
            "error": None
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        args.ref = "test_session/test_kernel"
        
        # Run command
        result = handle_interpreter_kernel_interrupt(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.interrupt_kernel.assert_called_once_with("test_session/test_kernel")
        
        # Check output
        output = self.stdout.getvalue()
        self.assertIn("interrupted successfully", output)
    
    @patch('DevAgent.__main__.create_interpreter')
    def test_handle_interpreter_kernel_delete(self, mock_interpreter):
        """Test handling the interpreter kernel delete command."""
        # Set up mock
        mock_instance = mock_interpreter.return_value
        mock_instance.delete_kernel.return_value = {
            "success": True,
            "error": None
        }
        
        # Set up args
        args = MagicMock()
        args.dir = self.temp_dir
        args.ref = "test_session/test_kernel"
        
        # Run command
        result = handle_interpreter_kernel_delete(args)
        
        # Verify results
        self.assertTrue(result)
        mock_interpreter.assert_called_once_with(pathlib.Path(self.temp_dir))
        mock_instance.delete_kernel.assert_called_once_with("test_session/test_kernel")
        
        # Check output
        output = self.stdout.getvalue()
        self.assertIn("deleted successfully", output)


if __name__ == "__main__":
    unittest.main()