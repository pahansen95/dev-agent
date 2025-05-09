import json
import os
import time
import glob
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Type, TypeVar, Iterator, Set
import uuid
from dataclasses import asdict

from ..domain.events import DomainEvent
from .event_serialization import serialize_event, deserialize_event

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=DomainEvent)

class FileSystemEventStore:
    """Event store that persists events to the filesystem."""

    def __init__(self, base_dir: Path):
        """
        Initialize the file system event store.

        Args:
            base_dir: The base directory for all event storage
        """
        self.base_dir = base_dir
        self.events_dir = base_dir / "events" / "streams"
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def append(self, event: DomainEvent) -> None:
        """
        Append an event to its type-specific stream.

        Args:
            event: The domain event to append
        """
        # Get event type
        event_type = type(event).__name__

        # Create event type directory if it doesn't exist
        event_type_dir = self.events_dir / event_type
        event_type_dir.mkdir(exist_ok=True)

        # Create event file with microsecond-precision timestamp
        timestamp = event.timestamp
        microseconds = int((timestamp - int(timestamp)) * 1000000)
        timestamp_str = f"{int(timestamp):010d}_{microseconds:06d}_{uuid.uuid4().hex[:8]}"
        event_file = event_type_dir / f"{timestamp_str}.json"

        # Serialize event to dictionary
        event_data = serialize_event(event)

        # Write event to file atomically
        self._atomic_write_json(event_file, event_data)

        logger.debug(f"Appended event {event_type} to stream at {event_file}")

    def get_events(self, event_type: Type[T], after_timestamp: float = 0) -> List[T]:
        """
        Get events of a specific type, optionally after a given timestamp.

        Args:
            event_type: The type of events to retrieve
            after_timestamp: Only retrieve events after this timestamp

        Returns:
            List of events of the requested type
        """
        # Get event type name
        event_type_name = event_type.__name__

        # Get event type directory
        event_type_dir = self.events_dir / event_type_name
        if not event_type_dir.exists():
            return []

        # Get event files
        event_files = sorted(event_type_dir.glob("*.json"))

        # Parse event files into events
        events = []
        for event_file in event_files:
            # Extract timestamp from filename
            try:
                filename = event_file.name
                file_timestamp = float(filename.split("_")[0])

                # Skip events before the cutoff
                if file_timestamp <= after_timestamp:
                    continue

                # Read and deserialize event
                event_data = self._atomic_read_json(event_file)
                if event_data:
                    event = deserialize_event(event_data)
                    if event and isinstance(event, event_type):
                        events.append(event)
            except Exception as e:
                logger.error(f"Error parsing event file {event_file}: {e}")

        return events

    def get_event_types(self) -> Set[str]:
        """
        Get all event types present in the store.

        Returns:
            Set of event type names
        """
        if not self.events_dir.exists():
            return set()

        return {path.name for path in self.events_dir.glob("*") if path.is_dir()}

    def get_event_stream(self, event_type: Type[T], from_timestamp: float = 0) -> Iterator[T]:
        """
        Get an iterator over events of a specific type.

        Args:
            event_type: The type of events to retrieve
            from_timestamp: Start iterating from this timestamp

        Returns:
            Iterator over events
        """
        # Get event type name
        event_type_name = event_type.__name__

        # Get event type directory
        event_type_dir = self.events_dir / event_type_name
        if not event_type_dir.exists():
            return iter([])

        # Get event files
        event_files = sorted(event_type_dir.glob("*.json"))

        # Create generator to yield events
        for event_file in event_files:
            # Extract timestamp from filename
            try:
                filename = event_file.name
                file_timestamp = float(filename.split("_")[0])

                # Skip events before the cutoff
                if file_timestamp <= from_timestamp:
                    continue

                # Read and deserialize event
                event_data = self._atomic_read_json(event_file)
                if event_data:
                    event = deserialize_event(event_data)
                    if event and isinstance(event, event_type):
                        yield event
            except Exception as e:
                logger.error(f"Error parsing event file {event_file}: {e}")

    def prune_events(self, event_type: Type[T], before_timestamp: float) -> int:
        """
        Delete events of a specific type before a given timestamp.

        Args:
            event_type: The type of events to prune
            before_timestamp: Delete events before this timestamp

        Returns:
            Number of events deleted
        """
        # Get event type name
        event_type_name = event_type.__name__

        # Get event type directory
        event_type_dir = self.events_dir / event_type_name
        if not event_type_dir.exists():
            return 0

        # Get event files before the timestamp
        event_files = []
        for event_file in event_type_dir.glob("*.json"):
            filename = event_file.name
            try:
                file_timestamp = float(filename.split("_")[0])
                if file_timestamp < before_timestamp:
                    event_files.append(event_file)
            except Exception:
                continue

        # Delete the files
        deleted_count = 0
        for event_file in event_files:
            try:
                event_file.unlink()
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting event file {event_file}: {e}")

        logger.info(f"Pruned {deleted_count} events of type {event_type_name} before {before_timestamp}")
        return deleted_count

    def _atomic_write_json(self, path: Path, data: Dict[str, Any]) -> None:
        """
        Write JSON data to a file atomically.

        Args:
            path: The path to write to
            data: The data to write
        """
        # Create parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to a temporary file first
        temp_path = path.with_suffix(".tmp")
        try:
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)

            # Replace the file atomically
            os.replace(temp_path, path)
        except Exception as e:
            logger.error(f"Error writing JSON to {path}: {e}")
            # Clean up temp file if it still exists
            try:
                os.unlink(temp_path)
            except (OSError, FileNotFoundError):
                pass
            raise

    def _atomic_read_json(self, path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Read JSON data from a file, returning default if file doesn't exist.

        Args:
            path: The path to read from
            default: The default value to return if the file doesn't exist

        Returns:
            The read data or the default
        """
        if default is None:
            default = {}

        if not path.exists():
            return default

        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {path}: {e}")
            return default
        except Exception as e:
            logger.error(f"Error reading JSON from {path}: {e}")
            return default