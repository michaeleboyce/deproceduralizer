import argparse
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, List

from tqdm import tqdm

from common import (
    NDJSONReader,
    NDJSONWriter,
    StateManager,
    setup_logging,
    PIPELINE_VERSION,
)

logger = setup_logging(__name__)

class BasePipeline(ABC):
    """
    Abstract base class for pipeline scripts.
    
    Handles:
    - Argument parsing
    - State management (checkpointing)
    - NDJSON reading/writing
    - Progress tracking
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(name)
        self.args = None
        self.state = None
        self.input_file = None
        self.output_file = None
        
    def setup(self):
        """Set up argument parser and state management."""
        parser = argparse.ArgumentParser(description=self.description)
        self.add_arguments(parser)
        self.args = parser.parse_args()
        
        self.input_file = Path(self.args.input_file)
        self.output_file = Path(self.args.output_file)
        
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
            
        # Set up state management
        state_file = Path(f"data/interim/{self.name}.state")
        self.state = StateManager(str(state_file))
        
        self.logger.info(f"Starting {self.name} pipeline")
        self.logger.info(f"Pipeline version: {PIPELINE_VERSION}")
        self.logger.info(f"Input: {self.input_file}")
        self.logger.info(f"Output: {self.output_file}")
        
    def add_arguments(self, parser: argparse.ArgumentParser):
        """Add arguments to the parser. Can be overridden by subclasses."""
        parser.add_argument(
            "--in",
            dest="input_file",
            required=True,
            help="Input NDJSON file"
        )
        parser.add_argument(
            "--out",
            dest="output_file",
            required=True,
            help="Output NDJSON file"
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of items to process"
        )

    @abstractmethod
    def process_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single item.
        
        Args:
            item: Input record
            
        Returns:
            Processed record (dict) or None to skip/filter out.
        """
        pass

    def get_items(self) -> List[Dict[str, Any]]:
        """
        Get items to process. 
        Default implementation reads from input NDJSON.
        Can be overridden for custom loading logic.
        """
        items = []
        reader = NDJSONReader(str(self.input_file))
        for item in reader:
            items.append(item)
            if self.args.limit and len(items) >= self.args.limit:
                break
        return items

    def run(self):
        """Main execution loop."""
        try:
            self.setup()
            
            items = self.get_items()
            total_items = len(items)
            self.logger.info(f"Found {total_items} items to process")
            
            processed_count = self.state.get("processed_count", 0)
            success_count = self.state.get("success_count", 0)
            error_count = self.state.get("error_count", 0)
            
            # Open output file (append mode handled by NDJSONWriter)
            with NDJSONWriter(str(self.output_file)) as writer:
                for i, item in enumerate(tqdm(items, desc=f"Running {self.name}", unit="item")):
                    # Skip if already processed
                    if i < processed_count:
                        continue
                        
                    try:
                        result = self.process_item(item)
                        if result:
                            writer.write(result)
                            success_count += 1
                    except Exception as e:
                        self.logger.error(f"Error processing item {i}: {e}")
                        error_count += 1
                        
                    processed_count += 1
                    
                    # Save state periodically
                    if processed_count % 10 == 0:
                        self.state.set("processed_count", processed_count)
                        self.state.set("success_count", success_count)
                        self.state.set("error_count", error_count)
                        self.state.save()
                        
            # Final state save
            self.state.set("processed_count", processed_count)
            self.state.set("success_count", success_count)
            self.state.set("error_count", error_count)
            self.state.save()
            
            self.logger.info(f"Pipeline complete!")
            self.logger.info(f"  Total processed: {processed_count}")
            self.logger.info(f"  Successful: {success_count}")
            self.logger.info(f"  Errors: {error_count}")
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise

