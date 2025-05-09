import logging
import time
import uuid
from typing import Callable, Dict, List, Type, TypeVar, Any, Optional, Set
from pathlib import Path
import threading

from ..domain.events import DomainEvent
from .event_store import FileSystemEventStore
from .event_consumer import EventConsumer
from .event_serialization import deserialize_event

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=DomainEvent)

class FileSystemEventBus:
    """Event bus implementation backed by the filesystem."""
    
    def __init__(self, base_dir: Path, consumer_id: Optional[str] = None):
        """
        Initialize the filesystem event bus.
        
        Args:
            base_dir: The base directory for all event storage
            consumer_id: The unique ID of this consumer, generated if None
        """
        self.base_dir = base_dir
        self.consumer_id = consumer_id or f"consumer-{uuid.uuid4().hex[:8]}"
        self.event_store = FileSystemEventStore(base_dir)
        self.consumer = EventConsumer(base_dir, self.consumer_id)
        self._subscribers: Dict[Type, List[Callable]] = {}
        self._last_poll_time: Dict[Type, float] = {}
        self._poll_lock = threading.RLock()
        logger.debug(f"Initialized FileSystemEventBus with consumer_id={self.consumer_id}")
    
    def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to the event store and notify subscribers.
        
        Args:
            event: The domain event to publish
        """
        # Store event in the filesystem
        self.event_store.append(event)
        
        # Notify in-memory subscribers
        event_type = type(event)
        subscribers = self._subscribers.get(event_type, [])
        
        logger.debug(f"Publishing event {event_type.__name__} to {len(subscribers)} subscribers")
        
        for subscriber in subscribers:
            try:
                subscriber(event)
            except Exception as e:
                logger.error(f"Error handling event {event_type.__name__}: {e}")
                
        # Update our consumer position
        self.consumer.update_position(event_type.__name__, event.timestamp)
    
    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """
        Subscribe to a specific event type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: The function to call when an event of this type is published
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
        logger.debug(f"Added subscriber to {event_type.__name__}, total: {len(self._subscribers[event_type])}")
    
    def unsubscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """
        Unsubscribe from a specific event type.
        
        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler function to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Removed subscriber from {event_type.__name__}, remaining: {len(self._subscribers[event_type])}")
            except ValueError:
                logger.warning(f"Handler not found for event type {event_type.__name__}")
    
    def poll_events(self, event_types: Optional[List[Type[DomainEvent]]] = None) -> int:
        """
        Poll for new events and notify subscribers.
        
        Args:
            event_types: List of event types to poll, or all subscribed types if None
            
        Returns:
            Number of events processed
        """
        with self._poll_lock:
            # Determine event types to poll
            types_to_poll = set(event_types or self._subscribers.keys())
            if not types_to_poll:
                return 0
            
            # Process events for each type
            total_processed = 0
            for event_type in types_to_poll:
                # Get the last position for this event type
                event_type_name = event_type.__name__
                last_position = self.consumer.get_last_position(event_type_name)
                
                # Get new events
                try:
                    events = self.event_store.get_events(event_type, last_position)
                    
                    # Process events
                    if events:
                        logger.debug(f"Processing {len(events)} events of type {event_type_name}")
                        
                        # Sort by timestamp to ensure correct order
                        events.sort(key=lambda e: e.timestamp)
                        
                        # Process each event
                        last_timestamp = last_position
                        for event in events:
                            # Call handlers
                            subscribers = self._subscribers.get(event_type, [])
                            for subscriber in subscribers:
                                try:
                                    subscriber(event)
                                except Exception as e:
                                    logger.error(f"Error handling event {event_type_name}: {e}")
                            
                            # Update last timestamp
                            last_timestamp = max(last_timestamp, event.timestamp)
                            total_processed += 1
                        
                        # Update consumer position
                        self.consumer.update_position(event_type_name, last_timestamp)
                except Exception as e:
                    logger.error(f"Error polling events for {event_type_name}: {e}")
            
            return total_processed
    
    def get_tracked_event_types(self) -> Set[str]:
        """
        Get all event types being tracked by this consumer.
        
        Returns:
            Set of event type names
        """
        return self.consumer.get_tracked_event_types()
    
    def mark_up_to_date(self, event_type: Type[DomainEvent]) -> None:
        """
        Mark an event type as fully consumed up to the current time.
        
        Args:
            event_type: The type of event
        """
        self.consumer.mark_up_to_date(event_type.__name__)