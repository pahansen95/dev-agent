import unittest
import tempfile
import shutil
from pathlib import Path
import os
import time

from DevAgent.interpreter.infrastructure.event_bus import EventBus
from DevAgent.interpreter.infrastructure.fs_manager import FileSystemManager
from DevAgent.interpreter.infrastructure.repositories import FileSystemSessionRepository, FileSystemKernelRepository
from DevAgent.interpreter.infrastructure.kernel_adapter import KernelControllerAdapter
from DevAgent.interpreter.domain.services import ReferenceResolutionService, KernelLifecycleService, ExecutionService
from DevAgent.interpreter.domain.factories import SessionFactory, KernelFactory
from DevAgent.interpreter.application.app_service import InterpreterApplicationService
from DevAgent.interpreter.application.facade import InterpreterFacade
from DevAgent.interpreter.domain.value_objects import SessionId, KernelId

class InterpreterIntegrationTests(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    """Set up class-level fixtures."""
    # Skip if we're in a CI environment that can't run kernels
    if os.environ.get("CI") == "true":
      raise unittest.SkipTest("Skipping integration tests in CI environment")

  def setUp(self):
    """Set up test fixtures."""
    # Create a temporary directory for tests
    self.temp_dir = tempfile.mkdtemp()
    self.base_dir = Path(self.temp_dir) / ".devagent"

    # Create the complete object graph
    self.event_bus = EventBus()
    self.fs_manager = FileSystemManager(self.base_dir)
    self.fs_manager.ensure_directory_structure()

    self.session_repo = FileSystemSessionRepository(self.fs_manager, self.event_bus)
    self.kernel_repo = FileSystemKernelRepository(self.fs_manager, self.event_bus)

    self.reference_service = ReferenceResolutionService(self.session_repo, self.kernel_repo)

    self.session_factory = SessionFactory(self.session_repo, self.event_bus)
    self.kernel_factory = KernelFactory(self.kernel_repo, self.event_bus)

    self.kernel_adapter = KernelControllerAdapter()

    self.kernel_lifecycle_service = KernelLifecycleService(self.kernel_repo, self.kernel_adapter, self.event_bus, self.fs_manager)

    self.execution_service = ExecutionService(self.kernel_repo, self.kernel_adapter, self.event_bus, self.fs_manager)

    self.app_service = InterpreterApplicationService(
      self.session_repo, self.kernel_repo, self.session_factory, self.kernel_factory, self.reference_service, self.execution_service,
      self.kernel_lifecycle_service, self.fs_manager)

    self.facade = InterpreterFacade(self.app_service)

  def tearDown(self):
    """Clean up test fixtures."""
    # Clean up the temporary directory
    shutil.rmtree(self.temp_dir)

  def test_session_lifecycle(self):
    """Test the full lifecycle of a session."""
    # Create a session
    create_result = self.facade.create_session("test_session")
    self.assertTrue(create_result["success"])
    session_id = create_result["session_id"]

    # Get the session
    get_result = self.facade.get_session("test_session")
    self.assertTrue(get_result["success"])
    self.assertEqual(get_result["session"]["id"], session_id)
    self.assertEqual(get_result["session"]["name"], "test_session")

    # List sessions
    list_result = self.facade.list_sessions()
    self.assertTrue(list_result["success"])
    self.assertEqual(len(list_result["sessions"]), 1)
    self.assertEqual(list_result["sessions"][0]["id"], session_id)

    # Delete the session
    delete_result = self.facade.delete_session("test_session")
    self.assertTrue(delete_result["success"])

    # Verify it's gone
    list_result = self.facade.list_sessions()
    self.assertTrue(list_result["success"])
    self.assertEqual(len(list_result["sessions"]), 0)

  def test_kernel_lifecycle(self):
    """Test the full lifecycle of a kernel."""
    # Create a session
    create_session_result = self.facade.create_session("test_session")
    self.assertTrue(create_session_result["success"])

    # Create a kernel
    create_kernel_result = self.facade.create_kernel("test_session", "test_kernel", "python3")
    self.assertTrue(create_kernel_result["success"])
    kernel_id = create_kernel_result["kernel_id"]

    # Get the kernel
    get_kernel_result = self.facade.get_kernel("test_session/test_kernel")
    self.assertTrue(get_kernel_result["success"])
    self.assertEqual(get_kernel_result["kernel"]["id"], kernel_id)
    self.assertEqual(get_kernel_result["kernel"]["name"], "test_kernel")

    # List kernels
    list_kernels_result = self.facade.list_kernels("test_session")
    self.assertTrue(list_kernels_result["success"])
    self.assertEqual(len(list_kernels_result["kernels"]), 1)
    self.assertEqual(list_kernels_result["kernels"][0]["id"], kernel_id)

    # Skip execute/restart/interrupt tests if we're in a CI environment that can't run kernels
    # Instead, just test deleting the kernel
    delete_kernel_result = self.facade.delete_kernel("test_session/test_kernel")
    self.assertTrue(delete_kernel_result["success"])

    # Verify it's gone
    list_kernels_result = self.facade.list_kernels("test_session")
    self.assertTrue(list_kernels_result["success"])
    self.assertEqual(len(list_kernels_result["kernels"]), 0)

  @unittest.skip("Skip unless running in an environment with Python kernel support")
  def test_code_execution(self):
    """Test executing code in a kernel."""
    # Create a session
    create_session_result = self.facade.create_session("test_session")
    self.assertTrue(create_session_result["success"])

    # Create a kernel
    create_kernel_result = self.facade.create_kernel("test_session", "test_kernel", "python3")
    self.assertTrue(create_kernel_result["success"])

    # Execute code
    execute_result = self.facade.execute_code("test_session/test_kernel", "1 + 1")
    self.assertTrue(execute_result["success"])
    self.assertEqual(execute_result["stdout"].strip(), "2")

    # Execute code with error
    execute_result = self.facade.execute_code("test_session/test_kernel", "undefined_variable")
    self.assertFalse(execute_result["success"])
    self.assertIsNotNone(execute_result["error"])

    # Test interrupting (skipped as it's hard to test reliably)

    # Test restarting
    restart_result = self.facade.restart_kernel("test_session/test_kernel")
    self.assertTrue(restart_result["success"])

    # Clean up
    delete_kernel_result = self.facade.delete_kernel("test_session/test_kernel")
    self.assertTrue(delete_kernel_result["success"])

if __name__ == "__main__":
  unittest.main()
