import unittest
from unittest.mock import MagicMock, patch
import time

from DevAgent.interpreter.domain.model import Session, Kernel
from DevAgent.interpreter.domain.value_objects import SessionId, KernelId, ExecutionResult
from DevAgent.interpreter.domain.exceptions import KernelNotFoundError, KernelAlreadyExistsError

class KernelTests(unittest.TestCase):

  def setUp(self):
    """Set up test fixtures."""
    self.session_id = SessionId.generate()
    self.kernel_id = KernelId.generate()
    self.kernel = Kernel(id=self.kernel_id, name="test_kernel", session_id=self.session_id, kernel_type="python3", _is_alive=False)

  def test_kernel_properties(self):
    """Test basic kernel properties."""
    self.assertEqual(self.kernel.id, self.kernel_id)
    self.assertEqual(self.kernel.name, "test_kernel")
    self.assertEqual(self.kernel.session_id, self.session_id)
    self.assertEqual(self.kernel.kernel_type, "python3")
    self.assertFalse(self.kernel.is_alive)

  def test_update_last_activity(self):
    """Test updating the last activity timestamp."""
    old_timestamp = self.kernel.last_activity
    time.sleep(0.001) # Ensure timestamp changes
    self.kernel.update_last_activity()
    self.assertGreater(self.kernel.last_activity, old_timestamp)

  def test_kernel_lifecycle_methods(self):
    """Test that lifecycle methods are present as stubs."""
    # These methods are implemented by infrastructure, but should exist in the model
    self.assertTrue(hasattr(self.kernel, 'start'))
    self.assertTrue(hasattr(self.kernel, 'execute'))
    self.assertTrue(hasattr(self.kernel, 'interrupt'))
    self.assertTrue(hasattr(self.kernel, 'restart'))
    self.assertTrue(hasattr(self.kernel, 'shutdown'))

class SessionTests(unittest.TestCase):

  def setUp(self):
    """Set up test fixtures."""
    self.session_id = SessionId.generate()
    self.session = Session(id=self.session_id, name="test_session")

  def test_session_properties(self):
    """Test basic session properties."""
    self.assertEqual(self.session.id, self.session_id)
    self.assertEqual(self.session.name, "test_session")
    self.assertIsNotNone(self.session.created_at)
    self.assertIsNotNone(self.session.last_activity)
    self.assertEqual(self.session.list_kernels(), [])

  def test_add_kernel(self):
    """Test adding a kernel to a session."""
    kernel_id = KernelId.generate()
    kernel = Kernel(id=kernel_id, name="python", session_id=self.session_id, kernel_type="python3")

    # Add kernel
    self.session.add_kernel(kernel)

    # Verify it was added
    kernels = self.session.list_kernels()
    self.assertEqual(len(kernels), 1)
    self.assertEqual(kernels[0].id, kernel_id)

    # Try to add again - should raise exception
    with self.assertRaises(KernelAlreadyExistsError):
      self.session.add_kernel(kernel)

  def test_get_kernel(self):
    """Test getting a kernel from a session."""
    # Add a kernel
    kernel_id = KernelId.generate()
    kernel = Kernel(id=kernel_id, name="python", session_id=self.session_id, kernel_type="python3")
    self.session.add_kernel(kernel)

    # Get by ID
    retrieved = self.session.get_kernel(kernel_id)
    self.assertEqual(retrieved.id, kernel_id)

    # Get by name
    retrieved = self.session.get_kernel_by_name("python")
    self.assertEqual(retrieved.id, kernel_id)

    # Get non-existent kernel by ID
    with self.assertRaises(KernelNotFoundError):
      self.session.get_kernel(KernelId.generate())

    # Get non-existent kernel by name
    self.assertIsNone(self.session.get_kernel_by_name("non-existent"))

  def test_remove_kernel(self):
    """Test removing a kernel from a session."""
    # Add a kernel
    kernel_id = KernelId.generate()
    kernel = Kernel(id=kernel_id, name="python", session_id=self.session_id, kernel_type="python3")
    self.session.add_kernel(kernel)

    # Verify it was added
    self.assertEqual(len(self.session.list_kernels()), 1)

    # Remove kernel
    self.session.remove_kernel(kernel_id)

    # Verify it was removed
    self.assertEqual(len(self.session.list_kernels()), 0)

    # Try to remove again - should raise exception
    with self.assertRaises(KernelNotFoundError):
      self.session.remove_kernel(kernel_id)

  def test_update_last_activity(self):
    """Test updating the last activity timestamp."""
    old_timestamp = self.session.last_activity
    time.sleep(0.001) # Ensure timestamp changes
    self.session.update_last_activity()
    self.assertGreater(self.session.last_activity, old_timestamp)

  def test_has_kernel_with_name(self):
    """Test checking if a session has a kernel with a given name."""
    # Initially should have no kernels
    self.assertFalse(self.session.has_kernel_with_name("python"))

    # Add a kernel
    kernel_id = KernelId.generate()
    kernel = Kernel(id=kernel_id, name="python", session_id=self.session_id, kernel_type="python3")
    self.session.add_kernel(kernel)

    # Now should have a kernel with the name
    self.assertTrue(self.session.has_kernel_with_name("python"))
    self.assertFalse(self.session.has_kernel_with_name("non-existent"))

if __name__ == "__main__":
  unittest.main()
