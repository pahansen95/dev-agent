from collections import defaultdict
from typing import Callable, Dict, List, Type, TypeVar, Any
import logging

from ..domain.events import DomainEvent

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=DomainEvent)

class EventBus:
    """Simple event bus for publishing and subscribing to domain events."""
    
    def __init__(self):
        self._subscribers: Dict[Type, List[Callable]] = defaultdict(list)
    
    def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: The domain event to publish
        """
        event_type = type(event)
        subscribers = self._subscribers.get(event_type, [])
        
        logger.debug(f"Publishing event {event_type.__name__} to {len(subscribers)} subscribers")
        
        for subscriber in subscribers:
            try:
                subscriber(event)
            except Exception as e:
                logger.error(f"Error handling event {event_type.__name__}: {e}")
    
    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """
        Subscribe to a specific event type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: The function to call when an event of this type is published
        """
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