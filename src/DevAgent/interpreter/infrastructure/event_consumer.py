import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, Set, Optional

logger = logging.getLogger(__name__)

class EventConsumer:

  """Tracks consumption progress for a specific consumer."""

  def __init__(self, base_dir: Path, consumer_id: str):
    """
        Initialize a consumer tracker.
        
        Args:
            base_dir: The base directory for all event storage
            consumer_id: The unique ID of this consumer
        """
    self.base_dir = base_dir
    self.consumer_id = consumer_id
    self.consumer_dir = base_dir / "events" / "consumers" / consumer_id
    self.consumer_dir.mkdir(parents=True, exist_ok=True)
    self.positions_file = self.consumer_dir / "positions.json"
    self._positions_cache: Dict[str, float] = {}
    self._load_positions()

  def get_last_position(self, event_type: str) -> float:
    """
        Get the last consumed position for an event type.
        
        Args:
            event_type: The type of event
            
        Returns:
            The timestamp of the last consumed event, or 0 if none
        """
    return self._positions_cache.get(event_type, 0.0)

  def update_position(self, event_type: str, position: float) -> None:
    """
        Update the last consumed position for an event type.
        
        Args:
            event_type: The type of event
            position: The timestamp of the last consumed event
        """
    # Only update if the new position is greater than the current one
    current_position = self._positions_cache.get(event_type, 0.0)
    if position <= current_position:
      logger.debug(f"Position {position} is not greater than current {current_position} for {event_type}")
      return

    # Update cache
    self._positions_cache[event_type] = position

    # Write to disk
    self._save_positions()

    logger.debug(f"Updated position for {event_type} to {position}")

  def mark_up_to_date(self, event_type: str, current_time: Optional[float] = None) -> None:
    """
        Mark an event type as fully consumed up to the current time.
        
        Args:
            event_type: The type of event
            current_time: The timestamp to use, or current time if None
        """
    if current_time is None:
      current_time = time.time()

    self.update_position(event_type, current_time)

  def get_tracked_event_types(self) -> Set[str]:
    """
        Get all event types being tracked by this consumer.
        
        Returns:
            Set of event type names
        """
    return set(self._positions_cache.keys())

  def _load_positions(self) -> None:
    """Load positions from disk to cache."""
    if not self.positions_file.exists():
      self._positions_cache = {}
      return

    try:
      with open(self.positions_file, 'r') as f:
        self._positions_cache = json.load(f)
      logger.debug(f"Loaded positions for consumer {self.consumer_id}")
    except Exception as e:
      logger.error(f"Error loading positions for consumer {self.consumer_id}: {e}")
      self._positions_cache = {}

  def _save_positions(self) -> None:
    """Save positions from cache to disk."""
    try:
      # Create parent directory if it doesn't exist
      self.positions_file.parent.mkdir(parents=True, exist_ok=True)

      # Write to a temporary file first
      temp_path = self.positions_file.with_suffix(".tmp")
      with open(temp_path, 'w') as f:
        json.dump(self._positions_cache, f, indent=2)

      # Replace the file atomically
      os.replace(temp_path, self.positions_file)

      logger.debug(f"Saved positions for consumer {self.consumer_id}")
    except Exception as e:
      logger.error(f"Error saving positions for consumer {self.consumer_id}: {e}")
      # Clean up temp file if it still exists
      try:
        os.unlink(temp_path)
      except (OSError, FileNotFoundError):
        pass
