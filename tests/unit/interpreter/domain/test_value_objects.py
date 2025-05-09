import unittest
from pathlib import Path

from DevAgent.interpreter.domain.value_objects import (
    SessionId,
    KernelId,
    Reference,
    ExecutionResult
)

class SessionIdTests(unittest.TestCase):
    
    def test_create_session_id(self):
        """Test creating a SessionId."""
        session_id = SessionId("sid-12345678")
        self.assertEqual(session_id.value, "sid-12345678")
        self.assertEqual(str(session_id), "sid-12345678")
    
    def test_generate_session_id(self):
        """Test generating a unique SessionId."""
        session_id1 = SessionId.generate()
        session_id2 = SessionId.generate()
        
        # Check format
        self.assertTrue(str(session_id1).startswith("sid-"))
        self.assertEqual(len(str(session_id1)), 12)  # "sid-" + 8 hex chars
        
        # Check uniqueness
        self.assertNotEqual(session_id1, session_id2)
    
    def test_immutability(self):
        """Test that SessionId is immutable."""
        session_id = SessionId("sid-12345678")
        with self.assertRaises(Exception):
            session_id.value = "sid-87654321"

class KernelIdTests(unittest.TestCase):
    
    def test_create_kernel_id(self):
        """Test creating a KernelId."""
        kernel_id = KernelId("kid-12345678")
        self.assertEqual(kernel_id.value, "kid-12345678")
        self.assertEqual(str(kernel_id), "kid-12345678")
    
    def test_generate_kernel_id(self):
        """Test generating a unique KernelId."""
        kernel_id1 = KernelId.generate()
        kernel_id2 = KernelId.generate()
        
        # Check format
        self.assertTrue(str(kernel_id1).startswith("kid-"))
        self.assertEqual(len(str(kernel_id1)), 12)  # "kid-" + 8 hex chars
        
        # Check uniqueness
        self.assertNotEqual(kernel_id1, kernel_id2)
    
    def test_immutability(self):
        """Test that KernelId is immutable."""
        kernel_id = KernelId("kid-12345678")
        with self.assertRaises(Exception):
            kernel_id.value = "kid-87654321"

class ReferenceTests(unittest.TestCase):
    
    def test_create_reference(self):
        """Test creating a Reference."""
        ref = Reference(
            type="kernel",
            name_component="python",
            id_component=None,
            path=None
        )
        self.assertEqual(ref.type, "kernel")
        self.assertEqual(ref.name_component, "python")
        self.assertIsNone(ref.id_component)
        self.assertIsNone(ref.path)
    
    def test_parse_session_name(self):
        """Test parsing a session name reference."""
        ref = Reference.parse("main")
        self.assertEqual(ref.type, "session")
        self.assertEqual(ref.name_component, "main")
        self.assertIsNone(ref.id_component)
    
    def test_parse_session_id(self):
        """Test parsing a session ID reference."""
        ref = Reference.parse("sid-12345678")
        self.assertEqual(ref.type, "session")
        self.assertIsNone(ref.name_component)
        self.assertEqual(ref.id_component, "sid-12345678")
    
    def test_parse_kernel_id(self):
        """Test parsing a kernel ID reference."""
        ref = Reference.parse("kid-12345678")
        self.assertEqual(ref.type, "kernel")
        self.assertIsNone(ref.name_component)
        self.assertEqual(ref.id_component, "kid-12345678")
    
    def test_parse_kernel_name(self):
        """Test parsing a kernel name reference."""
        ref = Reference.parse("main/python")
        self.assertEqual(ref.type, "kernel")
        self.assertEqual(ref.name_component, "python")
    
    def test_immutability(self):
        """Test that Reference is immutable."""
        ref = Reference(type="session", name_component="main")
        with self.assertRaises(Exception):
            ref.type = "kernel"

class ExecutionResultTests(unittest.TestCase):
    
    def test_create_execution_result(self):
        """Test creating an ExecutionResult."""
        result = ExecutionResult(
            success=True,
            stdout="Hello, world!",
            error=None,
            outputs=[{"output_type": "stream", "text": "Hello, world!"}],
            execution_time=0.1
        )
        self.assertTrue(result.success)
        self.assertEqual(result.stdout, "Hello, world!")
        self.assertIsNone(result.error)
        self.assertEqual(len(result.outputs), 1)
        self.assertEqual(result.execution_time, 0.1)
    
    def test_error_result(self):
        """Test creating an error ExecutionResult."""
        result = ExecutionResult(
            success=False,
            stdout="",
            error="NameError: name 'undefined_variable' is not defined",
            outputs=[],
            execution_time=0.05
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "NameError: name 'undefined_variable' is not defined")
    
    def test_immutability(self):
        """Test that ExecutionResult is immutable."""
        result = ExecutionResult(success=True, stdout="Hello, world!")
        with self.assertRaises(Exception):
            result.success = False

if __name__ == "__main__":
    unittest.main()