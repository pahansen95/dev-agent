import unittest
from unittest.mock import MagicMock
import time

from DevAgent.interpreter.infrastructure.event_bus import EventBus
from DevAgent.interpreter.domain.events import SessionCreated, KernelCreated
from DevAgent.interpreter.domain.value_objects import SessionId, KernelId

class EventBusTests(unittest.TestCase):

  def setUp(self):
    """Set up test fixtures."""
    self.event_bus = EventBus()

  def test_subscribe_and_publish(self):
    """Test subscribing to and publishing events."""
    # Create a mock handler
    handler = MagicMock()

    # Subscribe to an event
    self.event_bus.subscribe(SessionCreated, handler)

    # Create and publish an event
    session_id = SessionId.generate()
    event = SessionCreated(session_id=session_id, name="test_session")
    self.event_bus.publish(event)

    # Verify the handler was called
    handler.assert_called_once()

    # Verify the event was passed to the handler
    args, _ = handler.call_args
    received_event = args[0]
    self.assertEqual(received_event.session_id, session_id)
    self.assertEqual(received_event.name, "test_session")

  def test_multiple_subscribers(self):
    """Test multiple subscribers for the same event."""
    # Create mock handlers
    handler1 = MagicMock()
    handler2 = MagicMock()

    # Subscribe to an event
    self.event_bus.subscribe(SessionCreated, handler1)
    self.event_bus.subscribe(SessionCreated, handler2)

    # Create and publish an event
    session_id = SessionId.generate()
    event = SessionCreated(session_id=session_id, name="test_session")
    self.event_bus.publish(event)

    # Verify both handlers were called
    handler1.assert_called_once()
    handler2.assert_called_once()

  def test_different_event_types(self):
    """Test subscribing to different event types."""
    # Create mock handlers
    session_handler = MagicMock()
    kernel_handler = MagicMock()

    # Subscribe to different event types
    self.event_bus.subscribe(SessionCreated, session_handler)
    self.event_bus.subscribe(KernelCreated, kernel_handler)

    # Create and publish a session event
    session_id = SessionId.generate()
    session_event = SessionCreated(session_id=session_id, name="test_session")
    self.event_bus.publish(session_event)

    # Create and publish a kernel event
    kernel_id = KernelId.generate()
    kernel_event = KernelCreated(kernel_id=kernel_id, session_id=session_id, kernel_type="python3", name="test_kernel")
    self.event_bus.publish(kernel_event)

    # Verify each handler was called exactly once
    session_handler.assert_called_once()
    kernel_handler.assert_called_once()

    # Verify the correct events were passed to each handler
    session_args, _ = session_handler.call_args
    received_session_event = session_args[0]
    self.assertEqual(received_session_event.session_id, session_id)

    kernel_args, _ = kernel_handler.call_args
    received_kernel_event = kernel_args[0]
    self.assertEqual(received_kernel_event.kernel_id, kernel_id)

  def test_unsubscribe(self):
    """Test unsubscribing from events."""
    # Create a mock handler
    handler = MagicMock()

    # Subscribe to an event
    self.event_bus.subscribe(SessionCreated, handler)

    # Create an event
    session_id = SessionId.generate()
    event = SessionCreated(session_id=session_id, name="test_session")

    # Publish the event
    self.event_bus.publish(event)

    # Verify the handler was called
    handler.assert_called_once()
    handler.reset_mock()

    # Unsubscribe from the event
    self.event_bus.unsubscribe(SessionCreated, handler)

    # Publish the event again
    self.event_bus.publish(event)

    # Verify the handler was not called
    handler.assert_not_called()

  def test_error_handling(self):
    """Test that errors in handlers are caught."""

    # Create a handler that raises an exception
    def error_handler(event):
      raise ValueError("Test error")

    # Subscribe to an event
    self.event_bus.subscribe(SessionCreated, error_handler)

    # Create an event
    session_id = SessionId.generate()
    event = SessionCreated(session_id=session_id, name="test_session")

    # Publish the event - should not raise an exception
    try:
      self.event_bus.publish(event)
    except ValueError:
      self.fail("publish() raised ValueError unexpectedly!")

if __name__ == "__main__":
  unittest.main()
