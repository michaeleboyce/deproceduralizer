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
import pickle
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from tqdm import tqdm

# Pipeline version for tracking data lineage
PIPELINE_VERSION = "0.1.0"

# Log directory configuration
LOG_DIR = Path(os.getenv("PIPELINE_LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / os.getenv("PIPELINE_LOG_FILE", "pipeline.log")


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

        # Get file size to validate state offset
        file_size = self.file_path.stat().st_size if self.file_path.exists() else 0
        saved_offset = state_manager.get_byte_offset() if state_manager else 0

        # Reset offset if it's beyond current file size (stale state)
        if saved_offset > file_size:
            logging.warning(
                f"State offset ({saved_offset}) exceeds file size ({file_size}). "
                "Resetting to start (stale state detected)."
            )
            self.start_offset = 0
            if state_manager:
                state_manager.set_byte_offset(0)
                state_manager.save()
        else:
            self.start_offset = saved_offset

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


class TqdmLoggingHandler(logging.Handler):
    """
    Logging handler that routes messages through tqdm.write()
    to avoid breaking progress bars.
    """
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up logging with console (tqdm-safe) and file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Check if handler already exists to avoid duplicates
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - [%(threadName)s] - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = TqdmLoggingHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Prevent propagation to root logger which might have default handlers
        logger.propagate = False
        
    return logger


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


# Deduplication utilities

def load_dedup_map() -> Dict[str, str]:
    """
    Load section deduplication map from preprocessor output.

    Returns:
        Dict mapping section_id -> canonical_section_id for duplicates.
        Empty dict if no dedup map exists.
    """
    dedup_file = Path("data/interim/section_deduplication_map.pkl")
    if not dedup_file.exists():
        logging.info("No deduplication map found, proceeding without deduplication")
        return {}

    with open(dedup_file, "rb") as f:
        dedup_map = pickle.load(f)

    logging.info(f"Loaded deduplication map with {len(dedup_map)} duplicate mappings")
    return dedup_map


def get_canonical_id(section_id: str, dedup_map: Dict[str, str]) -> str:
    """
    Get canonical section ID for a given section, using dedup map if available.

    Args:
        section_id: Original section ID
        dedup_map: Deduplication mapping dict

    Returns:
        Canonical section ID (or original if not a duplicate)
    """
    return dedup_map.get(section_id, section_id)


# NDJSON convenience functions

def load_sections_ndjson(file_path: str) -> List[Dict[str, Any]]:
    """Load all sections from an NDJSON file into memory."""
    sections = []
    with open(file_path, "r") as f:
        for line in f:
            if line.strip():
                sections.append(json.loads(line))
    return sections


def save_json(data: Any, file_path: str) -> None:
    """Save data to a JSON file with pretty formatting."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def log_stage_header(stage_number: str, stage_name: str) -> None:
    """Print a formatted header for a pipeline stage."""
    header = f"STAGE {stage_number}: {stage_name}"
    separator = "=" * len(header)
    print("\n" + separator)
    print(header)
    print(separator + "\n")


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
