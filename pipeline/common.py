"""
Common utilities for deproceduralizer pipeline scripts.

Provides:
- NDJSON reading/writing with resume capability
- State/checkpoint management
- Progress tracking
- Logging setup
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from tqdm import tqdm

# Pipeline version for tracking data lineage
PIPELINE_VERSION = "0.1.0"


class StateManager:
    """Manage .state files for resumable processing."""

    def __init__(self, state_file: str):
        self.state_file = Path(state_file)
        self.state: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load state from file if it exists."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                self.state = json.load(f)
            logging.info(f"Loaded state from {self.state_file}")
        else:
            logging.info(f"No existing state file at {self.state_file}")

    def save(self) -> None:
        """Save current state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from state."""
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in state."""
        self.state[key] = value

    def get_byte_offset(self) -> int:
        """Get the last processed byte offset (for resuming file reads)."""
        return self.get("byte_offset", 0)

    def set_byte_offset(self, offset: int) -> None:
        """Set the byte offset and save."""
        self.set("byte_offset", offset)
        self.save()


class NDJSONReader:
    """Read NDJSON files with resume capability."""

    def __init__(self, file_path: str, state_manager: Optional[StateManager] = None):
        self.file_path = Path(file_path)
        self.state_manager = state_manager
        self.start_offset = (
            state_manager.get_byte_offset() if state_manager else 0
        )

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over records, resuming from saved offset if available."""
        with open(self.file_path, "r") as f:
            if self.start_offset > 0:
                f.seek(self.start_offset)
                logging.info(
                    f"Resuming from byte offset {self.start_offset}"
                )

            # Read line by line manually to track position
            while True:
                # Track position before reading
                current_pos = f.tell()
                line = f.readline()

                if not line:
                    break  # EOF

                if line.strip():
                    try:
                        record = json.loads(line)
                        yield record

                        # Update offset after successful parse
                        if self.state_manager:
                            # Position is now after this line
                            self.state_manager.set_byte_offset(f.tell())

                    except json.JSONDecodeError as e:
                        logging.error(f"Invalid JSON at offset {current_pos}: {e}")
                        continue


class NDJSONWriter:
    """Write NDJSON files atomically."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_handle = None

    def __enter__(self):
        self.file_handle = open(self.file_path, "a")  # Append mode for resume
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file_handle:
            self.file_handle.close()

    def write(self, record: Dict[str, Any]) -> None:
        """Write a single record as a JSON line."""
        if not self.file_handle:
            raise RuntimeError("NDJSONWriter not opened (use 'with' statement)")

        json_line = json.dumps(record, ensure_ascii=False)
        self.file_handle.write(json_line + "\n")
        self.file_handle.flush()  # Ensure written to disk


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up logging with consistent format."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(name)


def count_lines(file_path: str) -> int:
    """Count lines in a file (for progress bars)."""
    with open(file_path, "r") as f:
        return sum(1 for _ in f)


def validate_record(record: Dict[str, Any], required_fields: list[str]) -> bool:
    """Validate that a record has all required fields."""
    for field in required_fields:
        if field not in record:
            logging.error(f"Missing required field '{field}' in record: {record.get('id', 'unknown')}")
            return False
    return True


# Example usage:
"""
from common import StateManager, NDJSONReader, NDJSONWriter, setup_logging

logger = setup_logging(__name__)
state = StateManager("data/interim/my_script.state")

# Reading with resume
reader = NDJSONReader("input.ndjson", state_manager=state)
for record in reader:
    process(record)

# Writing
with NDJSONWriter("output.ndjson") as writer:
    writer.write({"id": "dc-1-101", "text": "..."})
"""
