"""
Base loader class for loading NDJSON data into Postgres with resume capability.

This abstract base class eliminates ~200-300 lines of duplicate code across loaders.

Features:
- Batch inserts (configurable size)
- Resume from checkpoint (.state file with byte offset)
- Progress bar with tqdm
- Error handling and statistics
- Consistent logging and reporting

Subclasses must implement:
- _insert_batch(cursor, batch): Define SQL INSERT/UPDATE logic
- validate_record(record) [optional]: Validate individual records before batching
"""

import json
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from tqdm import tqdm


class BaseLoader(ABC):
    """Abstract base class for all NDJSON data loaders.

    Provides common functionality for checkpoint/resume, progress tracking,
    batch processing, and error handling.

    Subclasses must implement _insert_batch() with specific SQL logic.
    """

    def __init__(
        self,
        database_url: str,
        input_file: Path,
        batch_size: int = 500,
        state_file: Optional[Path] = None,
        jurisdiction: str = "dc"
    ):
        """Initialize the loader.

        Args:
            database_url: PostgreSQL connection string
            input_file: Path to input NDJSON file
            batch_size: Number of records to batch before inserting
            state_file: Path to checkpoint state file (default: input_file.state)
            jurisdiction: Jurisdiction code (default: 'dc')
        """
        self.database_url = database_url
        self.input_file = Path(input_file)
        self.batch_size = batch_size
        self.state_file = Path(state_file) if state_file else self.input_file.with_suffix('.state')
        self.jurisdiction = jurisdiction

        # Statistics
        self.inserted_count = 0
        self.updated_count = 0
        self.error_count = 0
        self.skipped_count = 0

    def get_checkpoint(self) -> int:
        """Get the last processed byte offset from state file.

        Returns:
            Byte offset to resume from (0 if no checkpoint exists)
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return data.get('byte_offset', 0)
            except (json.JSONDecodeError, FileNotFoundError):
                return 0
        return 0

    def save_checkpoint(self, byte_offset: int):
        """Save current byte offset and statistics to state file.

        Args:
            byte_offset: Current position in input file
        """
        with open(self.state_file, 'w') as f:
            json.dump({
                'byte_offset': byte_offset,
                'inserted': self.inserted_count,
                'updated': self.updated_count,
                'errors': self.error_count,
                'skipped': self.skipped_count,
                'jurisdiction': self.jurisdiction
            }, f, indent=2)

    def count_lines(self) -> int:
        """Count total lines in input file for progress bar.

        Returns:
            Number of lines in input file
        """
        with open(self.input_file, 'r') as f:
            return sum(1 for _ in f)

    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate a single record before adding to batch.

        Override this method in subclasses to add custom validation.

        Args:
            record: Single NDJSON record as dict

        Returns:
            True if record is valid, False to skip
        """
        # Default: accept all records
        return True

    @abstractmethod
    def _insert_batch(self, cursor, batch: List[Dict[str, Any]]):
        """Insert a batch of records into the database.

        Subclasses must implement this method with specific SQL INSERT/UPDATE logic.

        Args:
            cursor: psycopg2 cursor
            batch: List of validated records to insert

        Should update self.inserted_count, self.updated_count, or self.error_count as appropriate.
        Should raise exceptions on errors (will be caught by run() method).
        """
        pass

    def _retry_with_backoff(self, func, *args, max_retries=3, **kwargs):
        """
        Retry a function with exponential backoff.

        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result of func

        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                # Transient database errors - retry
                last_exception = e
                if attempt < max_retries - 1:
                    delay = 2 ** attempt  # 1s, 2s, 4s
                    print(f"\n⚠ Database error (attempt {attempt + 1}/{max_retries}), retrying in {delay}s: {str(e)[:100]}", file=sys.stderr)
                    time.sleep(delay)
                else:
                    print(f"\n✗ Database error after {max_retries} attempts: {str(e)[:100]}", file=sys.stderr)
            except Exception as e:
                # Non-transient errors - don't retry
                raise

        raise last_exception

    def run(self):
        """Main execution method - loads data from NDJSON file into database.

        Handles:
        - Checkpoint resume
        - Progress tracking
        - Batch processing
        - Error handling
        - Statistics reporting
        """
        # Get starting position from checkpoint
        start_offset = self.get_checkpoint()

        # Count total lines for progress bar
        total_lines = self.count_lines()

        # Log resume if applicable
        if start_offset > 0:
            print(f"Resuming from byte offset {start_offset}")

        # Connect to database
        conn = psycopg2.connect(self.database_url)
        conn.autocommit = False
        cursor = conn.cursor()

        try:
            batch = []
            current_offset = 0
            lines_processed = 0

            with open(self.input_file, 'r') as f:
                # Skip to checkpoint
                if start_offset > 0:
                    f.seek(start_offset)
                    current_offset = start_offset

                # Calculate initial lines_processed for progress bar
                # (Approximate based on byte offset and average line length)
                if start_offset > 0:
                    file_size = self.input_file.stat().st_size
                    lines_processed = int((start_offset / file_size) * total_lines)

                # Progress bar
                loader_name = self.__class__.__name__
                pbar = tqdm(
                    total=total_lines,
                    initial=lines_processed,
                    desc=f"Loading ({loader_name})",
                    unit="records"
                )

                for line in f:
                    try:
                        record = json.loads(line)

                        # Validate record
                        if not self.validate_record(record):
                            self.skipped_count += 1
                            lines_processed += 1
                            pbar.update(1)
                            continue

                        # Add jurisdiction if not present
                        if 'jurisdiction' not in record:
                            record['jurisdiction'] = self.jurisdiction

                        batch.append(record)

                        # Process batch when full
                        if len(batch) >= self.batch_size:
                            self._retry_with_backoff(self._insert_batch, cursor, batch)
                            conn.commit()
                            batch = []

                            # Update checkpoint
                            current_offset = f.tell()
                            self.save_checkpoint(current_offset)

                        lines_processed += 1
                        pbar.update(1)
                        pbar.set_postfix({
                            'inserted': self.inserted_count,
                            'errors': self.error_count,
                            'skipped': self.skipped_count
                        })

                    except json.JSONDecodeError as e:
                        self.error_count += 1
                        print(f"\nError parsing JSON at line {lines_processed}: {e}", file=sys.stderr)
                        lines_processed += 1
                        pbar.update(1)
                        continue

                    except Exception as e:
                        # Rollback the failed transaction to recover
                        conn.rollback()
                        self.error_count += 1
                        print(f"\nError processing record at line {lines_processed}: {e}", file=sys.stderr)
                        lines_processed += 1
                        pbar.update(1)
                        continue

                # Process remaining batch
                if batch:
                    self._retry_with_backoff(self._insert_batch, cursor, batch)
                    conn.commit()
                    self.save_checkpoint(f.tell())

                pbar.close()

            # Final report
            print(f"\n✓ Load complete:")
            print(f"  - Inserted/Updated: {self.inserted_count}")
            print(f"  - Errors: {self.error_count}")
            print(f"  - Skipped: {self.skipped_count}")
            print(f"  - Total processed: {lines_processed}")

        except Exception as e:
            conn.rollback()
            print(f"\nFatal error during load: {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()
            conn.close()

    def get_loader_name(self) -> str:
        """Get a human-readable name for this loader.

        Returns:
            Loader class name without 'Loader' suffix
        """
        name = self.__class__.__name__
        return name.replace('Loader', '') if name.endswith('Loader') else name
