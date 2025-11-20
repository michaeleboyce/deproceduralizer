import time
import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Manages rate limits for different models.
    Tracks requests per minute (RPM) and requests per day (RPD).
    """
    def __init__(self):
        # Track calls per model: model_name -> {"minute_calls": [], "day_calls": 0, "day_start": date}
        self.model_trackers = {}
        # Track model blocks: model_name -> retry_timestamp (None if not blocked)
        self.model_blocks = {}
        self.lock = Lock()  # Protect concurrent access

    def _get_tracker(self, model_config: dict):
        """Get or initialize tracker for a model."""
        name = model_config["name"]
        today = datetime.utcnow().date()

        if name not in self.model_trackers:
            self.model_trackers[name] = {
                "minute_calls": [],
                "day_calls": 0,
                "day_start": today
            }

        tracker = self.model_trackers[name]

        # Reset daily counter if new day
        if tracker["day_start"] != today:
            tracker["day_calls"] = 0
            tracker["day_start"] = today

        return tracker

    def wait_if_needed(self, model_config: dict, *, block: bool = True) -> bool:
        """
        Check if model can be used based on rate limits.

        Returns:
            True if model can be used (after waiting, if requested), False to skip to next model
        """
        model_name = model_config["name"]

        while True:
            # FIRST: Check if this specific model is blocked from API error responses
            is_blocked, seconds_remaining = self.is_model_blocked(model_name)
            if is_blocked:
                minutes = int(seconds_remaining // 60)
                seconds = int(seconds_remaining % 60)
                logger.debug(f"Skipping {model_name} (blocked for {minutes}m {seconds}s)")
                return False

            with self.lock:
                now = datetime.utcnow()
                tracker = self._get_tracker(model_config)

                # Clean up old minute calls (older than 60s)
                current_timestamp = now.timestamp()
                tracker["minute_calls"] = [t for t in tracker["minute_calls"] if current_timestamp - t < 60]

                # Check daily limit
                if tracker["day_calls"] >= model_config["rpd"]:
                    wait_seconds = (datetime.combine((now + timedelta(days=1)).date(), datetime.min.time()) - now).total_seconds()
                    logger.debug(f"Daily limit reached for {model_config['name']} (wait {wait_seconds:.0f}s)")

                    # Mark the model as blocked until the next day to avoid hammering
                    if block and wait_seconds > 0:
                        self.block_model(model_name, time.time() + wait_seconds, "Daily quota reached")
                    return False

                # Check minute limit
                if len(tracker["minute_calls"]) >= model_config["rpm"]:
                    # Oldest call in the last minute determines next allowed timestamp
                    oldest_call = min(tracker["minute_calls"])
                    wait_seconds = max(0.0, 60 - (current_timestamp - oldest_call))

                    if not block:
                        logger.debug(f"Minute limit reached for {model_config['name']}")
                        return False

                    # Release lock before sleeping to avoid blocking other threads
                    logger.debug(f"Minute limit reached for {model_config['name']} - sleeping {wait_seconds:.2f}s")
                else:
                    # Within limits, safe to proceed
                    return True

            # Sleep happens outside the lock to allow other threads to progress
            if block and wait_seconds > 0:
                time.sleep(wait_seconds)
                continue

            return False

    def record_call(self, model_config: dict):
        """Record a successful call to a model."""
        with self.lock:
            tracker = self._get_tracker(model_config)
            tracker["minute_calls"].append(datetime.utcnow().timestamp())
            tracker["day_calls"] += 1

    def block_model(self, model_name: str, retry_timestamp: float, reason: str):
        """
        Block a specific model until the specified timestamp.

        Args:
            model_name: Name of the model to block
            retry_timestamp: Unix timestamp when model can be retried
            reason: Human-readable reason (e.g., "Daily quota exhausted")
        """
        with self.lock:
            self.model_blocks[model_name] = retry_timestamp
            retry_time = datetime.fromtimestamp(retry_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"🚫 Blocking {model_name} until {retry_time}: {reason}")

    def is_model_blocked(self, model_name: str) -> tuple[bool, Optional[float]]:
        """
        Check if a model is currently blocked.

        Returns:
            (is_blocked, seconds_until_retry)
        """
        with self.lock:
            block_until = self.model_blocks.get(model_name)

            if block_until is None:
                return (False, None)

            now = time.time()
            if now >= block_until:
                # Block has expired
                self.model_blocks[model_name] = None
                logger.info(f"✅ {model_name} block expired, retrying")
                return (False, None)

            seconds_remaining = block_until - now
            return (True, seconds_remaining)
