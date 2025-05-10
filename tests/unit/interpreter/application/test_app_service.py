import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from DevAgent.interpreter.application.app_service import InterpreterApplicationService
from DevAgent.interpreter.domain.value_objects import SessionId, KernelId, ExecutionResult
from DevAgent.interpreter.domain.model import Session, Kernel
from DevAgent.interpreter.domain.exceptions import SessionError, KernelError
from DevAgent.interpreter.application.dtos import SessionDTO, KernelDTO, ExecutionResultDTO

class InterpreterApplicationServiceTests(unittest.TestCase):

  def setUp(self):
    """Set up test fixtures."""
    # Create mock repositories
    self.session_repo = MagicMock()
    self.kernel_repo = MagicMock()

    # Create mock factories
    self.session_factory = MagicMock()
    self.kernel_factory = MagicMock()

    # Create mock services
    self.reference_service = MagicMock()
    self.execution_service = MagicMock()
    self.kernel_lifecycle_service = MagicMock()

    # Create mock filesystem manager
    self.fs_manager = MagicMock()
    self.fs_manager.get_session_path.return_value = Path("/tmp/sessions/sid-12345678")
    self.fs_manager.get_kernel_path.return_value = Path("/tmp/sessions/sid-12345678/kernels/kid-12345678")

    # Create application service
    self.app_service = InterpreterApplicationService(
      session_repo=self.session_repo,
      kernel_repo=self.kernel_repo,
      session_factory=self.session_factory,
      kernel_factory=self.kernel_factory,
      reference_service=self.reference_service,
      execution_service=self.execution_service,
      kernel_lifecycle_service=self.kernel_lifecycle_service,
      fs_manager=self.fs_manager)

  def test_create_session_success(self):
    """Test creating a session successfully."""
    # Set up mock session factory
    session_id = SessionId.generate()
    session = Session(id=session_id, name="test_session")
    self.session_factory.create_session.return_value = session

    # Call the service
    result = self.app_service.create_session("test_session")

    # Verify result
    self.assertTrue(result.success)
    self.assertEqual(result.session_id, str(session_id))
    self.assertIsNone(result.error)

    # Verify mock was called
    self.session_factory.create_session.assert_called_once_with("test_session")

  def test_create_session_failure(self):
    """Test creating a session with failure."""
    # Set up mock session factory to raise an exception
    self.session_factory.create_session.side_effect = SessionError("Session already exists")

    # Call the service
    result = self.app_service.create_session("test_session")

    # Verify result
    self.assertFalse(result.success)
    self.assertIsNone(result.session_id)
    self.assertEqual(result.error, "Session already exists")

    # Verify mock was called
    self.session_factory.create_session.assert_called_once_with("test_session")

  def test_get_session_success(self):
    """Test getting a session successfully."""
    # Set up mock reference service
    session_id = SessionId.generate()
    session = Session(id=session_id, name="test_session")
    self.reference_service.resolve_to_session.return_value = session

    # Set up mock kernel repository
    self.kernel_repo.find_by_session_id.return_value = []

    # Call the service
    result = self.app_service.get_session("test_session")

    # Verify result
    self.assertTrue(result.success)
    self.assertIsNotNone(result.session)
    self.assertEqual(result.session.id, str(session_id))
    self.assertEqual(result.session.name, "test_session")
    self.assertEqual(result.session.kernel_count, 0)
    self.assertIsNone(result.error)

    # Verify mocks were called
    self.reference_service.resolve_to_session.assert_called_once_with("test_session")
    self.kernel_repo.find_by_session_id.assert_called_once_with(session_id)

  def test_get_session_not_found(self):
    """Test getting a session that doesn't exist."""
    # Set up mock reference service
    self.reference_service.resolve_to_session.return_value = None

    # Call the service
    result = self.app_service.get_session("test_session")

    # Verify result
    self.assertFalse(result.success)
    self.assertIsNone(result.session)
    self.assertEqual(result.error, "Session not found: test_session")

    # Verify mock was called
    self.reference_service.resolve_to_session.assert_called_once_with("test_session")

  def test_create_kernel_success(self):
    """Test creating a kernel successfully."""
    # Set up mock reference service
    session_id = SessionId.generate()
    session = Session(id=session_id, name="test_session")
    self.reference_service.resolve_to_session.return_value = session

    # Set up mock kernel factory
    kernel_id = KernelId.generate()
    kernel = Kernel(id=kernel_id, name="test_kernel", session_id=session_id, kernel_type="python3")
    self.kernel_factory.create_kernel.return_value = kernel

    # Call the service
    result = self.app_service.create_kernel("test_session", "test_kernel", "python3")

    # Verify result
    self.assertTrue(result.success)
    self.assertEqual(result.kernel_id, str(kernel_id))
    self.assertIsNone(result.error)

    # Verify mocks were called
    self.reference_service.resolve_to_session.assert_called_once_with("test_session")
    self.kernel_factory.create_kernel.assert_called_once_with(session, "test_kernel", "python3")
    self.kernel_lifecycle_service.start_kernel.assert_called_once_with(kernel)

  def test_create_kernel_session_not_found(self):
    """Test creating a kernel in a session that doesn't exist."""
    # Set up mock reference service
    self.reference_service.resolve_to_session.return_value = None

    # Call the service
    result = self.app_service.create_kernel("test_session", "test_kernel", "python3")

    # Verify result
    self.assertFalse(result.success)
    self.assertIsNone(result.kernel_id)
    self.assertEqual(result.error, "Session not found: test_session")

    # Verify mock was called
    self.reference_service.resolve_to_session.assert_called_once_with("test_session")
    self.kernel_factory.create_kernel.assert_not_called()

  def test_execute_code_success(self):
    """Test executing code successfully."""
    # Set up mock reference service
    kernel_id = KernelId.generate()
    session_id = SessionId.generate()
    kernel = Kernel(id=kernel_id, name="test_kernel", session_id=session_id, kernel_type="python3", _is_alive=True)
    self.reference_service.resolve_to_kernel.return_value = kernel

    # Set up mock execution service
    execution_result = ExecutionResult(success=True, stdout="Hello, world!", error=None, outputs=[], execution_time=0.1)
    self.execution_service.execute_code.return_value = execution_result

    # Call the service
    result = self.app_service.execute_code("test_session/test_kernel", "print('Hello, world!')")

    # Verify result
    self.assertTrue(result.success)
    self.assertIsNotNone(result.result)
    self.assertEqual(result.result.stdout, "Hello, world!")
    self.assertIsNone(result.error)

    # Verify mocks were called
    self.reference_service.resolve_to_kernel.assert_called_once_with("test_session/test_kernel")
    self.execution_service.execute_code.assert_called_once_with(kernel, "print('Hello, world!')")

  def test_execute_code_kernel_not_found(self):
    """Test executing code in a kernel that doesn't exist."""
    # Set up mock reference service
    self.reference_service.resolve_to_kernel.return_value = None

    # Call the service
    result = self.app_service.execute_code("test_session/test_kernel", "print('Hello, world!')")

    # Verify result
    self.assertFalse(result.success)
    self.assertIsNone(result.result)
    self.assertEqual(result.error, "Kernel not found: test_session/test_kernel")

    # Verify mock was called
    self.reference_service.resolve_to_kernel.assert_called_once_with("test_session/test_kernel")
    self.execution_service.execute_code.assert_not_called()

  def test_execute_code_execution_error(self):
    """Test executing code with an execution error."""
    # Set up mock reference service
    kernel_id = KernelId.generate()
    session_id = SessionId.generate()
    kernel = Kernel(id=kernel_id, name="test_kernel", session_id=session_id, kernel_type="python3", _is_alive=True)
    self.reference_service.resolve_to_kernel.return_value = kernel

    # Set up mock execution service to raise an exception
    self.execution_service.execute_code.side_effect = KernelError("Kernel execution failed")

    # Call the service
    result = self.app_service.execute_code("test_session/test_kernel", "print('Hello, world!')")

    # Verify result
    self.assertFalse(result.success)
    self.assertIsNone(result.result)
    self.assertEqual(result.error, "Kernel execution failed")

    # Verify mocks were called
    self.reference_service.resolve_to_kernel.assert_called_once_with("test_session/test_kernel")
    self.execution_service.execute_code.assert_called_once_with(kernel, "print('Hello, world!')")

if __name__ == "__main__":
  unittest.main()
