# LLM Cascade Strategies Comparison

This document compares the two available LLM cascade strategies in the deproceduralizer project.

## Strategy 1: Rate-Limited Cascade (Original)

**File:** `pipeline/llm_client.py`

### Approach
- **Preemptive Rate Limiting**: Checks rate limits *before* making API calls
- **Fixed Tier Order**: Gemini → Groq → OpenRouter → Ollama
- **Time-Based Retry**: Retries Gemini after 10 minutes (600 seconds)
- **Sticky Sessions**: OpenRouter uses sticky sessions (10-20 calls before retrying higher tiers)

### Key Features
```python
# Rate limiter checks BEFORE calling
if not self.rate_limiter.wait_if_needed(model_config):
    logger.debug(f"{model_name} rate limited, trying next model")
    continue

# Periodic retry of Gemini
should_retry_gemini = (
    using_fallback and
    (current_time - last_gemini_fail) >= GEMINI_RETRY_INTERVAL
)
```

### Pros
- Prevents wasting API calls on rate-limited models
- Predictable behavior with known rate limits
- Efficient use of API quotas

### Cons
- Can be overly conservative (skips models that might work)
- Fixed tier ordering doesn't adapt to actual availability
- Requires accurate rate limit configuration
- May skip working models due to rate limit estimates

---

## Strategy 2: Error-Driven Cascade (New)

**File:** `pipeline/llm_client_error_driven.py`

### Approach
- **Reactive Error Handling**: Tries models until they actually error
- **Dynamic Ordering**: Models reorder based on success/failure
- **Attempt-Based Retry**: Retries failed models after 100 attempts (not time-based)
- **FIFO Retry Queue**: First model to fail is first to be retried

### Key Features
```python
# Active stack of working models
self.active_models = [model1, model2, model3, ...]

# Failed queue with retry logic: [(model, failed_at_attempt, num_failures)]
self.failed_queue = [
    (model_config, 150, 2),  # Failed at attempt 150, 2 times total
    (model_config, 200, 1),  # Failed at attempt 200, 1 time total
]

# Retry logic - check every call
ready_for_retry = []
for model_config, failed_at, num_failures in self.failed_queue:
    if self.total_attempts - failed_at >= 100:
        ready_for_retry.append((model_config, failed_at, num_failures))

# FIFO: first to fail is first to retry
if ready_for_retry:
    model_to_retry = ready_for_retry[0]  # Pop first (FIFO)
    # Try model...
    if success:
        # Move to TOP of active stack
        self.active_models.insert(0, model_config)
    else:
        # Move back to END of failed queue
        self.failed_queue.append((model_config, current_attempt, num_failures + 1))
```

### Pros
- Maximizes use of available models (tries until actual error)
- Adapts dynamically to changing API availability
- No need for accurate rate limit configuration
- Successful models stay at top of stack (better performance)
- Failed models automatically move to back of queue

### Cons
- May make more "failed" API calls initially
- Uses attempt-based retry rather than time-based
- Could hit rate limits more aggressively

---

## Visual Comparison

### Rate-Limited Cascade Flow
```
Call 1:  Gemini-2.5-flash ✓
Call 2:  Gemini-2.5-flash ✓
...
Call 10: Gemini-2.5-flash ✓ (hit RPM limit)
Call 11: [SKIP - rate limited] → Gemini-2.5-flash-lite ✓
Call 12: [SKIP - rate limited] → Gemini-2.5-flash-lite ✓
...
Call 25: [SKIP - all Gemini] → Groq-compound ✓
...
[After 10 minutes]
Call 100: Gemini-2.5-flash ✓ (retry successful)
```

### Error-Driven Cascade Flow
```
Call 1:  Gemini-2.5-flash ✓
Call 2:  Gemini-2.5-flash ✓
...
Call 10: Gemini-2.5-flash ✓
Call 11: Gemini-2.5-flash ✗ (429 rate limit error)
         → Move to failed queue: [(gemini-2.5-flash, 11, 1)]
Call 12: Gemini-2.5-flash-lite ✓
...
Call 111: [100 attempts since failure] → Retry gemini-2.5-flash ✓
          → Move to TOP of active stack!
Call 112: Gemini-2.5-flash ✓ (now preferred model)
Call 113: Gemini-2.5-flash ✓
```

---

## Active Stack vs Failed Queue

### Error-Driven Strategy State Management

**Active Stack** (priority-ordered, try first in list):
```python
# Models that are currently working
self.active_models = [
    {"name": "gemini-2.5-flash"},      # TOP - most preferred, working
    {"name": "gemini-2.0-flash"},
    {"name": "groq/compound"},
    {"name": "phi4-mini"},             # BOTTOM - least preferred fallback
]
```

**Failed Queue** (FIFO, retry after 100 attempts):
```python
# Models that have failed, waiting for retry
self.failed_queue = [
    ({"name": "gemini-2.5-flash-lite"}, 150, 2),  # FIRST to retry
    ({"name": "groq/compound-mini"}, 200, 1),
    ({"name": "llama-3.3-70b"}, 225, 1),          # LAST to retry
]
#  model_config                     ↑    ↑
#                    attempt_when_failed    num_failures
```

**Retry Logic**:
```python
# Current attempt: 250
# Check which models are ready:
#   - gemini-2.5-flash-lite: 250 - 150 = 100 ✓ Ready!
#   - groq/compound-mini: 250 - 200 = 50 ✗ Not yet
#   - llama-3.3-70b: 250 - 225 = 25 ✗ Not yet

# Retry gemini-2.5-flash-lite (FIFO - first to fail, first to retry)
result = try_model("gemini-2.5-flash-lite")

if result:
    # SUCCESS! Move to TOP of active stack
    self.active_models.insert(0, {"name": "gemini-2.5-flash-lite"})
    # Now active_models = [gemini-2.5-flash-lite, gemini-2.5-flash, ...]
else:
    # FAILED! Move to BACK of failed queue
    self.failed_queue.append(({"name": "gemini-2.5-flash-lite"}, 250, 3))
    # Will retry again after 100 more attempts (at attempt 350)
```

---

## When to Use Each Strategy

### Use Rate-Limited Cascade When:
- You have accurate rate limit information
- You want to conserve API quota carefully
- You prefer predictable, conservative behavior
- Time-based retries fit your workflow

### Use Error-Driven Cascade When:
- Rate limits are unknown or changing
- You want maximum model utilization
- You prefer adaptive, dynamic behavior
- Attempt-based retries fit your workflow
- You want successful models to stay at top priority

---

## Migration Guide

### Switching from Rate-Limited to Error-Driven

**Old code:**
```python
from pipeline.llm_client import LLMClient

client = LLMClient(cascade_strategy="extended")
result = client.generate(prompt, response_model, section_id)
```

**New code:**
```python
from pipeline.llm_client_error_driven import ErrorDrivenLLMClient

client = ErrorDrivenLLMClient()
result = client.generate(prompt, response_model, section_id)
```

**API is identical** - just change the import and class name!

---

## Configuration

### Error-Driven Cascade Configuration

Edit `pipeline/llm_client_error_driven.py`:

```python
# Change retry threshold (default: 100 attempts)
RETRY_AFTER_ATTEMPTS = 100  # Try different values: 50, 100, 150

# Modify model priority order
GEMINI_MODELS = [
    {"name": "gemini-2.5-flash", "tier": "gemini"},
    # Add or remove models as needed
]
```

---

## Statistics Comparison

### Rate-Limited Cascade Stats
```
============================================================
LLM USAGE STATISTICS
============================================================
Cascade Strategy: extended
Parallel Execution: Disabled
Session Duration: 15m 23s

Model Usage:
  gemini-2.5-flash: 234 calls (65.2%)
  groq/compound: 89 calls (24.8%)
  phi4-mini: 36 calls (10.0%)
  Total: 359 calls

Tier Performance:
  ├─ Gemini: 234 calls (8m 15s)
  ├─ Groq: 89 calls (5m 30s, 12 fallback periods)
  └─ Ollama: 36 calls (1m 38s, 3 fallback periods)

Tier Switches: 15 total
```

### Error-Driven Cascade Stats
```
======================================================================
ERROR-DRIVEN CASCADE - LLM USAGE STATISTICS
======================================================================
Strategy: Error-driven with FIFO retry after 100 attempts
Session Duration: 15m 23s
Total Attempts: 359

Current Cascade Status:
  Active Models: gemini-2.5-flash, gemini-2.0-flash, groq/compound
  Failed Queue (2 models):
    - gemini-2.5-flash-lite: 2 failures, retry in 45 attempts
    - llama-3.3-70b: 1 failures, retry in 78 attempts
  Retry In Progress: None

Model Usage:
  gemini-2.5-flash:
    ├─ Calls: 234 (65.2%)
    └─ Success Rate: 95.1% (234/246 attempts)
  groq/compound:
    ├─ Calls: 89 (24.8%)
    └─ Success Rate: 92.7% (89/96 attempts)
  phi4-mini:
    ├─ Calls: 36 (10.0%)
    └─ Success Rate: 100.0% (36/36 attempts)
  Total Successful Calls: 359

Model Switches: 15 total
======================================================================
```

---

## Testing

### Test the Error-Driven Client

```bash
# Basic test
python test_error_driven_client.py --test basic

# Multiple calls to observe cascade behavior
python test_error_driven_client.py --test multiple

# Monitor cascade status during execution
python test_error_driven_client.py --test status

# Run all tests
python test_error_driven_client.py --test all
```

---

## Summary

| Feature | Rate-Limited Cascade | Error-Driven Cascade |
|---------|---------------------|---------------------|
| **Rate Limiting** | Preemptive checks | Reactive to errors |
| **Model Ordering** | Fixed tiers | Dynamic (success-based) |
| **Retry Logic** | Time-based (10 min) | Attempt-based (100 calls) |
| **API Usage** | Conservative | Aggressive |
| **Adaptability** | Low | High |
| **Predictability** | High | Medium |
| **Best For** | Known rate limits | Unknown/changing limits |

**Recommendation**: Start with **Error-Driven Cascade** for better utilization and dynamic adaptation. Switch to Rate-Limited Cascade if you need stricter quota management.
