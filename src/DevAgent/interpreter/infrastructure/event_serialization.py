import json
import importlib
import inspect
import logging
from typing import Dict, Any, Type, Optional, List
from dataclasses import asdict, is_dataclass
import sys

from ..domain.events import DomainEvent
from ..domain.value_objects import SessionId, KernelId, KernelStatus

logger = logging.getLogger(__name__)

def serialize_event(event: DomainEvent) -> Dict[str, Any]:
  """
    Serialize an event to a dictionary for storage.
    
    Args:
        event: The event to serialize
        
    Returns:
        Dictionary representation of the event
    """
  if not is_dataclass(event):
    raise ValueError(f"Cannot serialize non-dataclass event: {type(event)}")

  # Convert event to dict
  event_dict = asdict(event)

  # Add event type information
  event_dict["_event_type"] = type(event).__name__
  event_dict["_event_module"] = type(event).__module__

  # Special handling for enum values
  for key, value in event_dict.items():
    if key.startswith("_"):
      continue

    if isinstance(value, KernelStatus):
      event_dict[key] = {"_type": "KernelStatus", "value": value.value}
    elif isinstance(value, SessionId):
      event_dict[key] = {"_type": "SessionId", "value": value.value}
    elif isinstance(value, KernelId):
      event_dict[key] = {"_type": "KernelId", "value": value.value}

  return event_dict

def deserialize_event(data: Dict[str, Any]) -> Optional[DomainEvent]:
  """
    Deserialize an event from stored data.
    
    Args:
        data: The serialized event data
        
    Returns:
        The deserialized event
    """
  if not isinstance(data, dict):
    logger.error(f"Cannot deserialize non-dict data: {type(data)}")
    return None

  event_type_name = data.pop("_event_type", None)
  event_module_name = data.pop("_event_module", None)

  if not event_type_name or not event_module_name:
    logger.error("Missing event type information in serialized data")
    return None

  try:
    # Import the module containing the event class
    module = importlib.import_module(event_module_name)

    # Get the event class
    event_class = getattr(module, event_type_name)

    # Process special types in the data
    processed_data = {}
    for key, value in data.items():
      if isinstance(value, dict) and "_type" in value:
        type_name = value["_type"]
        if type_name == "KernelStatus":
          processed_data[key] = KernelStatus(value["value"])
        elif type_name == "SessionId":
          processed_data[key] = SessionId(value["value"])
        elif type_name == "KernelId":
          processed_data[key] = KernelId(value["value"])
        else:
          processed_data[key] = value
      else:
        processed_data[key] = value

    # Create the event instance
    return event_class(**processed_data)
  except ImportError:
    logger.error(f"Could not import module {event_module_name}")
    return None
  except AttributeError:
    logger.error(f"Could not find event class {event_type_name} in module {event_module_name}")
    return None
  except Exception as e:
    logger.error(f"Error deserializing event: {e}")
    return None

def get_all_event_types() -> List[Type[DomainEvent]]:
  """
    Get all event classes defined in the domain.events module.
    
    Returns:
        List of event classes
    """
  from ..domain import events

  event_types = []
  for name, obj in inspect.getmembers(events):
    if inspect.isclass(obj) and hasattr(obj, "__dataclass_fields__") and obj.__module__ == events.__name__:
      event_types.append(obj)

  return event_types

def register_event_types() -> Dict[str, Type[DomainEvent]]:
  """
    Register all event types for deserialization.
    
    Returns:
        Dictionary mapping event type names to event classes
    """
  event_types = get_all_event_types()
  return {event_type.__name__: event_type for event_type in event_types}
